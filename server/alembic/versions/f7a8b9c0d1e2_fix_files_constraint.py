"""fix files constraint: drop md5 unique, add original_name unique

Revision ID: f7a8b9c0d1e2
Revises: 5e6ce5370710
Create Date: 2026-08-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = '5e6ce5370710'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    """检查约束是否已存在（兼容已有/未有约束的数据库）"""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for uk in insp.get_unique_constraints(table_name):
        if uk["name"] == constraint_name:
            return True
    return False


def upgrade() -> None:
    """修正约束：移除 (user_id, md5) UNIQUE，新增 (user_id, original_name) UNIQUE"""
    with op.batch_alter_table('files') as batch_op:
        if _constraint_exists('files', 'uq_files_user_md5'):
            batch_op.drop_constraint('uq_files_user_md5', type_='unique')
        if not _constraint_exists('files', 'uq_files_user_original_name'):
            batch_op.create_unique_constraint(
                'uq_files_user_original_name', ['user_id', 'original_name'],
            )


def downgrade() -> None:
    """回滚：移除 (user_id, original_name) UNIQUE，恢复 (user_id, md5) UNIQUE"""
    with op.batch_alter_table('files') as batch_op:
        if _constraint_exists('files', 'uq_files_user_original_name'):
            batch_op.drop_constraint('uq_files_user_original_name', type_='unique')
        if not _constraint_exists('files', 'uq_files_user_md5'):
            batch_op.create_unique_constraint(
                'uq_files_user_md5', ['user_id', 'md5'],
            )
