"""pg_baseline_148

Revision ID: pg_baseline_148
Revises: None
Create Date: 2026-10-26

NOTE: This migration is PostgreSQL-specific baseline derived from the latest
SQLAlchemy models. It must be applied on a PostgreSQL database before any
other Alembic upgrades. The same schema can be generated on SQLite by the
existing SQLite migration chain.

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'pg_baseline_148'
down_revision: Union[str, Sequence[str], None] = None
branch_labels = ('pg',)
depends_on = ()


def upgrade() -> None:
    """Apply PG baseline schema using SQLAlchemy metadata."""
    from app.core.database import Base, engine

    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    """Drop all tables."""
    from app.core.database import Base, engine

    Base.metadata.drop_all(bind=engine)
