"""138 迁移冒烟测试：两个 Alembic 迁移的 DDL 可在真实 SQLite 上执行

背景：迁移脚本中的 SQL 错误（如把 `sa.text(...)` 当作绑定参数）不会在测试或
启动阶段暴露，只会在生产 `alembic upgrade` 时炸。这里直接在临时库上执行
upgrade()，把 DDL 正确性纳入回归网。

不依赖 alembic CLI 的数据库连接（避免污染 .env 指向的库）。
"""

import importlib.util
import sys
import time
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401  注册全部模型到 Base.metadata
from app.core.database import Base

pytestmark = pytest.mark.fast

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"
MIGRATIONS = [
    "b7d41e0c9a35_files_md5_single_record.py",
    "d4e8b2f17c09_add_file_bindings_table.py",
]


def _run_upgrade(module_path: Path, conn) -> None:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(conn))
    module.upgrade()


@pytest.fixture()
def legacy_db(tmp_path):
    """构造迁移前的库：旧唯一约束 + 重复 (user_id, md5) 数据"""
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS uq_files_user_md5_active"))
        conn.execute(text("DROP TABLE IF EXISTS file_bindings"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_files_original_name ON files (original_name)"
            )
        )
        for i in range(2):
            conn.execute(
                text(
                    "INSERT INTO files (user_id, md5, original_name, rel_path, size_bytes,"
                    " mime_type, upload_source, ref_count, created_at)"
                    f" VALUES (1, 'dupmd5', 'dup{i}.jpg', 'gears/1/dup{i}.jpg', 10,"
                    " 'image/jpeg', 'gear_image', 1, 0)"
                )
            )
    yield engine
    engine.dispose()


def test_migrations_apply_on_legacy_db(legacy_db):
    """两个迁移按顺序执行后：旧约束移除、新索引与绑定表建立、重复记录合并"""
    with legacy_db.begin() as conn:
        for name in MIGRATIONS:
            _run_upgrade(VERSIONS_DIR / name, conn)

    insp = inspect(legacy_db)
    index_names = [i["name"] for i in insp.get_indexes("files")]

    assert "uq_files_original_name" not in index_names, "旧全局同名约束应被移除"
    assert "uq_files_user_md5_active" in index_names, "应建立 (user_id, md5) 部分唯一索引"
    assert "file_bindings" in insp.get_table_names()

    with legacy_db.begin() as conn:
        rows = conn.execute(
            text("SELECT id, ref_count, deleted_at FROM files WHERE md5='dupmd5' ORDER BY id")
        ).fetchall()

    assert len(rows) == 2
    keeper, merged = rows
    assert keeper[2] is None, "保留 id 最小的一条（未软删）"
    assert merged[2] is not None and merged[2] <= time.time(), "其余重复记录应被软删"


def test_partial_index_allows_reinsert_after_soft_delete(legacy_db):
    """部分唯一索引排除软删行：软删后可再次插入同 (user_id, md5)"""
    with legacy_db.begin() as conn:
        for name in MIGRATIONS:
            _run_upgrade(VERSIONS_DIR / name, conn)
        conn.execute(
            text("UPDATE files SET deleted_at = :ts WHERE md5='dupmd5'"), {"ts": time.time()}
        )
        conn.execute(
            text(
                "INSERT INTO files (user_id, md5, original_name, rel_path, size_bytes,"
                " mime_type, upload_source, ref_count, created_at)"
                " VALUES (1, 'dupmd5', 'again.jpg', 'gears/1/again.jpg', 10,"
                " 'image/jpeg', 'gear_image', 0, 0)"
            )
        )
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM files WHERE user_id=1 AND md5='dupmd5' AND deleted_at IS NULL"
            )
        ).scalar()

    assert count == 1
