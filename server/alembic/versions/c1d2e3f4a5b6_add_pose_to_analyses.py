"""add pose column to analyses

Revision ID: c1d2e3f4a5b6
Revises: 9e8d74e6ab01
Create Date: 2026-08-14

"""

import sqlalchemy as sa

from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "9e8d74e6ab01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("pose", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "pose")
