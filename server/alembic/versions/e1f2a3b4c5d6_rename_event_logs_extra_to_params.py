"""rename event_logs.extra to params

Revision ID: e1f2a3b4c5d6
Revises: d4e8b2f17c09
Create Date: 2026-09-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd4e8b2f17c09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite 3.25+ 支持 RENAME COLUMN，仅重命名列名，数据保留。
    # 旧数据 params 列可能残留历史 user_id 键（旧前端写入），无害不清理。
    op.execute("ALTER TABLE event_logs RENAME COLUMN extra TO params")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE event_logs RENAME COLUMN params TO extra")
