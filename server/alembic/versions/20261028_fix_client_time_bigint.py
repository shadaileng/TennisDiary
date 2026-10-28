"""fix event_logs client_time to BIGINT

Revision ID: 20261028_fix_client_time_bigint
Revises: pg_baseline_148
Create Date: 2026-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20261028_fix_client_time_bigint'
down_revision = 'pg_baseline_148'
branch_labels = None
depends_on = None


def upgrade():
    # 将 client_time 从 INTEGER 改为 BIGINT
    op.alter_column('event_logs', 'client_time',
               existing_type=sa.Integer,
               type_=sa.BigInteger,
               existing_nullable=True)


def downgrade():
    op.alter_column('event_logs', 'client_time',
               existing_type=sa.BigInteger,
               type_=sa.Integer,
               existing_nullable=True)
