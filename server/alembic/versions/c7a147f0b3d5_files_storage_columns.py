"""files 表新增 storage / storage_status 两列（147 阶段一 KODO 对象存储）

Revision ID: c7a147f0b3d5
Revises: e1f2a3b4c5d6
Create Date: 2026-10-26 11:30:00.000000

- `storage`：本体位置 local / kodo（多源并存时可扩 `kodo:bucket名`）
- `storage_status`：0=PENDING 未同步 / 1=SYNCED / 2=FAILED 待补偿
- `ix_files_storage_status`：补偿扫描索引（普通索引，SQLite 与 PG 双方言安全）
- 回填：存量行 `storage='local'`、`storage_status=1`（本地即真相，视为已同步；
  真正搬到 Kodo 后由同步中心/迁移脚本改写为 kodo）
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a147f0b3d5"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """加两列（带 server_default）→ 建索引 → 存量回填 local + SYNCED"""
    with op.batch_alter_table("files") as batch_op:
        batch_op.add_column(
            sa.Column("storage", sa.String(length=32), nullable=False, server_default="local")
        )
        batch_op.add_column(
            sa.Column("storage_status", sa.Integer(), nullable=False, server_default="0")
        )
    op.create_index("ix_files_storage_status", "files", ["storage_status"])

    op.execute("UPDATE files SET storage = 'local', storage_status = 1")


def downgrade() -> None:
    """删索引 + 删两列（batch 模式对 SQLite 的 DROP COLUMN 友好）"""
    op.drop_index("ix_files_storage_status", table_name="files")
    with op.batch_alter_table("files") as batch_op:
        batch_op.drop_column("storage_status")
        batch_op.drop_column("storage")
