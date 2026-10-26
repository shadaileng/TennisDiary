"""147 阶段一 Step 4：files 表新增 storage / storage_status 两列迁移冒烟

- 模型两列 + 索引 + 默认值（`server_default` 保证裸 SQL INSERT 也可用）
- Alembic `batch_alter_table` 在真实 SQLite 上 upgrade / downgrade 可执行
- 存量回填：`storage='local'`、`storage_status=1`（本地即真相，视为已同步）
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401  注册全部模型到 Base.metadata
from app.core.database import Base
from app.models.file import (
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)

pytestmark = pytest.mark.fast

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"
MIGRATION_FILE = VERSIONS_DIR / "c7a147f0b3d5_files_storage_columns.py"


def _load_and_run(module_path: Path, conn, *, upgrade: bool = True) -> None:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(conn))
    module.upgrade() if upgrade else module.downgrade()


@pytest.fixture()
def legacy_db(tmp_path):
    """构造迁移前的库：files 表无 storage / storage_status 两列，含一条存量行"""
    db_path = tmp_path / "legacy147.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        # 模拟迁移前 schema（模型已含新列，先删掉回到旧结构）
        conn.execute(text("DROP INDEX IF EXISTS ix_files_storage_status"))
        conn.execute(text("ALTER TABLE files DROP COLUMN storage_status"))
        conn.execute(text("ALTER TABLE files DROP COLUMN storage"))
        conn.execute(
            text(
                "INSERT INTO files (user_id, md5, original_name, rel_path, size_bytes,"
                " mime_type, upload_source, ref_count, created_at)"
                " VALUES (1, '0' || '1234567890abcdef1234567890abcde', 'old.jpg',"
                " 'gears/1/old.jpg', 10, 'image/jpeg', 'gear_image', 1, 0)"
            )
        )
    yield engine
    engine.dispose()


class TestModelColumns:
    def test_columns_exist_with_defaults(self):
        columns = {c.name: c for c in File.__table__.columns}
        assert "storage" in columns
        assert "storage_status" in columns
        assert columns["storage"].default.arg == "local"
        assert columns["storage"].server_default.arg == "local"
        assert columns["storage_status"].default.arg == 0
        assert columns["storage_status"].server_default.arg == "0"

    def test_status_index_registered(self):
        indexes = {ix.name for ix in File.__table__.indexes}
        assert "ix_files_storage_status" in indexes

    def test_status_constants(self):
        assert STORAGE_STATUS_PENDING == 0
        assert STORAGE_STATUS_SYNCED == 1

    def test_insert_applies_local_pending_defaults(self):
        """INSERT 时默认落 `local` + PENDING（列默认兜底，构造期不填充）"""
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO files (user_id, md5, rel_path, size_bytes)"
                        " VALUES (1, 'b1a2c3d4e5f607182930415263748590', 'gears/1/x.jpg', 1)"
                    )
                )
                row = conn.execute(text("SELECT storage, storage_status FROM files")).fetchone()
                assert row is not None
                assert row[0] == "local"
                assert row[1] == STORAGE_STATUS_PENDING
        finally:
            engine.dispose()


class TestMigration:
    def test_upgrade_adds_columns_and_backfills(self, legacy_db):
        with legacy_db.begin() as conn:
            _load_and_run(MIGRATION_FILE, conn, upgrade=True)

            inspector = inspect(conn)
            columns = {c["name"] for c in inspector.get_columns("files")}
            assert {"storage", "storage_status"} <= columns
            indexes = {ix["name"] for ix in inspector.get_indexes("files")}
            assert "ix_files_storage_status" in indexes

            row = conn.execute(
                text("SELECT storage, storage_status FROM files WHERE md5 LIKE '0%'")
            ).fetchone()
            assert row is not None
            assert row[0] == "local"
            assert row[1] == STORAGE_STATUS_SYNCED  # 存量：本地即真相 → 已同步

    def test_downgrade_drops_columns(self, legacy_db):
        with legacy_db.begin() as conn:
            _load_and_run(MIGRATION_FILE, conn, upgrade=True)
        with legacy_db.begin() as conn:
            _load_and_run(MIGRATION_FILE, conn, upgrade=False)
            inspector = inspect(conn)
            columns = {c["name"] for c in inspector.get_columns("files")}
            assert "storage" not in columns
            assert "storage_status" not in columns
