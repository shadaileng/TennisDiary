"""pg_baseline_148

Revision ID: pg_baseline_148
Revises:
Create Date: 2026-10-26

NOTE: This migration is PostgreSQL-specific baseline derived from the latest
SQLAlchemy models. It must be applied on a PostgreSQL database before any
other Alembic upgrades. The same schema can be generated on SQLite by the
existing SQLite migration chain.

"""
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'pg_baseline_148'
down_revision: Union[str, Sequence[str], None] = None  # New root for PG branch
branch_labels = ('pg',)
depends_on = ()


def upgrade() -> None:
    """Basline DDL: execute SQL from server/migrations/pg_baseline_148.sql."""
    # Locate the baseline file relative to this migration.
    # The file path is: server/migrations/pg_baseline_148.sql
    sql_path = Path(__file__).parent.parent.parent / 'migrations' / 'pg_baseline_148.sql'
    if not sql_path.exists():
        raise FileNotFoundError(f"PG baseline SQL not found: {sql_path}")

    # Read raw SQL (may contain multiple statements).
    sql = sql_path.read_text(encoding='utf-8')

    # Execute the entire batch as a single string.
    op.execute(sql)


def downgrade() -> None:
    """Revert: drop all tables (or drop the database and recreate)."""
    # For safety in CI, we drop all tables created by this migration.
    # The list of tables is derived from Base.metadata in the app.
    # Here we just delete the version stamp; actual cleanup is by dropping DB.
    op.execute("""
    DELETE FROM alembic_version WHERE version_num = 'pg_baseline_148'
    """)
    # Optional: DROP SCHEMA public CASCADE; CREATE SCHEMA public;
    # But we avoid because it may affect other DB objects.
