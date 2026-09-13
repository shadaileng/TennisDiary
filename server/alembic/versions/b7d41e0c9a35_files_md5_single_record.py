"""files: 移除全局同名约束，新增 (user_id, md5) 部分唯一索引（138 文件管理重构）

Revision ID: b7d41e0c9a35
Revises: 5281282bbc83
Create Date: 2026-09-07 14:05:00.000000

变更要点：
1. 合并同一 (user_id, md5) 的重复有效记录：保留 id 最小的一条，ref_count 求和，
   其余软删（唯一索引创建的前置条件，否则脏数据会导致建索引失败）
2. 删除 uq_files_original_name（MD5 命名后跨用户必然同名，该约束不再成立）
3. 新建部分唯一索引 uq_files_user_md5_active ON files(user_id, md5)
   WHERE deleted_at IS NULL（软删行被排除，允许重新上传）

物理文件重命名为 {md5}.{后缀} 由管理端「一键迁移」（migrate_to_md5）完成，
不在本迁移内做磁盘操作。
"""

import time
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d41e0c9a35"
down_revision: Union[str, Sequence[str], None] = "5281282bbc83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in insp.get_indexes(table_name))


def _constraint_kind(table_name: str, constraint_name: str) -> str | None:
    """判断唯一约束在 SQLite 中的存在形式：constraint / index / None

    SQLite 下 create_unique_constraint 往往落成 CREATE UNIQUE INDEX，
    反射时可能只出现在 get_indexes 而非 get_unique_constraints。
    """
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if any(uk["name"] == constraint_name for uk in insp.get_unique_constraints(table_name)):
        return "constraint"
    if any(idx["name"] == constraint_name for idx in insp.get_indexes(table_name)):
        return "index"
    return None


def _merge_duplicate_md5() -> None:
    """合并同用户同 MD5 的重复有效记录（保留 id 最小者，ref_count 求和）"""
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT user_id, md5, COUNT(*) AS cnt
            FROM files
            WHERE deleted_at IS NULL
            GROUP BY user_id, md5
            HAVING cnt > 1
            """
        )
    ).fetchall()

    if not duplicates:
        return

    for user_id, md5, _cnt in duplicates:
        rows = bind.execute(
            sa.text(
                """
                SELECT id, ref_count
                FROM files
                WHERE user_id = :user_id AND md5 = :md5 AND deleted_at IS NULL
                ORDER BY id ASC
                """
            ),
            {"user_id": user_id, "md5": md5},
        ).fetchall()

        keep_id = rows[0][0]
        total_ref = sum(int(row[1] or 0) for row in rows)
        drop_ids = [row[0] for row in rows[1:]]

        bind.execute(
            sa.text("UPDATE files SET ref_count = :ref WHERE id = :id"),
            {"ref": total_ref, "id": keep_id},
        )
        now_ts = int(time.time())
        for file_id in drop_ids:
            bind.execute(
                sa.text("UPDATE files SET ref_count = 0, deleted_at = :ts WHERE id = :id"),
                {"ts": float(now_ts), "id": file_id},
            )


def upgrade() -> None:
    """合并重复记录 → 删除全局同名约束 → 建立 (user_id, md5) 部分唯一索引"""
    _merge_duplicate_md5()

    kind = _constraint_kind("files", "uq_files_original_name")
    if kind == "constraint":
        with op.batch_alter_table("files") as batch_op:
            batch_op.drop_constraint("uq_files_original_name", type_="unique")
    elif kind == "index":
        op.drop_index("uq_files_original_name", table_name="files")

    if not _index_exists("files", "uq_files_user_md5_active"):
        op.create_index(
            "uq_files_user_md5_active",
            "files",
            ["user_id", "md5"],
            unique=True,
            sqlite_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    """回滚：删除部分唯一索引，恢复全局同名约束"""
    if _index_exists("files", "uq_files_user_md5_active"):
        op.drop_index("uq_files_user_md5_active", table_name="files")

    if _constraint_kind("files", "uq_files_original_name") is None:
        with op.batch_alter_table("files") as batch_op:
            batch_op.create_unique_constraint("uq_files_original_name", ["original_name"])
