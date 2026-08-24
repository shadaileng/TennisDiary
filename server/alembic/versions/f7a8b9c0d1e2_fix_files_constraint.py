"""fix files constraint: drop md5 unique, add original_name unique

Revision ID: f7a8b9c0d1e2
Revises: 5e6ce5370710
Create Date: 2026-08-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = '5e6ce5370710'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """修正约束：移除 (user_id, md5) UNIQUE，新增 (user_id, original_name) UNIQUE"""
    # 移除旧约束：同用户同 MD5 只能一条记录（阻断秒传新建记录）
    op.drop_constraint('uq_files_user_md5', 'files', type_='unique')

    # 新增约束：同用户不允许两个文件同名（冲突时上传端点重命名）
    op.create_unique_constraint(
        'uq_files_user_original_name', 'files',
        ['user_id', 'original_name'],
    )


def downgrade() -> None:
    """回滚：移除 (user_id, original_name) UNIQUE，恢复 (user_id, md5) UNIQUE"""
    op.drop_constraint('uq_files_user_original_name', 'files', type_='unique')
    op.create_unique_constraint(
        'uq_files_user_md5', 'files',
        ['user_id', 'md5'],
    )
