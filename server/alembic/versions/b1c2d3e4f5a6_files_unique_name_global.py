"""files unique name: drop per-user constraint, add global constraint

Revision ID: b1c2d3e4f5a6
Revises: a65795d7402d
Create Date: 2026-08-30 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a65795d7402d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for uk in insp.get_unique_constraints(table_name):
        if uk["name"] == constraint_name:
            return True
    return False


def upgrade() -> None:
    """移除 (user_id, original_name) UNIQUE，新增 (original_name) UNIQUE"""
    with op.batch_alter_table('files') as batch_op:
        if _constraint_exists('files', 'uq_files_user_original_name'):
            batch_op.drop_constraint('uq_files_user_original_name', type_='unique')
        if not _constraint_exists('files', 'uq_files_original_name'):
            batch_op.create_unique_constraint(
                'uq_files_original_name', ['original_name'],
            )


def downgrade() -> None:
    """回滚：移除 (original_name) UNIQUE，恢复 (user_id, original_name) UNIQUE"""
    with op.batch_alter_table('files') as batch_op:
        if _constraint_exists('files', 'uq_files_original_name'):
            batch_op.drop_constraint('uq_files_original_name', type_='unique')
        if not _constraint_exists('files', 'uq_files_user_original_name'):
            batch_op.create_unique_constraint(
                'uq_files_user_original_name', ['user_id', 'original_name'],
            )
