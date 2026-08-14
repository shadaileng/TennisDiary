"""ai_providers model -> models JSON list

Revision ID: 9e8d74e6ab01
Revises: 7e375669cd0d
Create Date: 2026-08-14 11:20:00.000000

"""
from typing import Sequence, Union

import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e8d74e6ab01'
down_revision: Union[str, Sequence[str], None] = '7e375669cd0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 新增 models（JSON 数组字符串）列，先允许空
    with op.batch_alter_table('ai_providers') as batch:
        batch.add_column(sa.Column('models', sa.Text(), nullable=True))

    # 2. 回填：旧 model -> models[0]
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, model FROM ai_providers")).fetchall()
    for row_id, model in rows:
        bind.execute(
            sa.text("UPDATE ai_providers SET models = :m WHERE id = :id"),
            {"m": json.dumps([model]), "id": row_id},
        )

    # 3. 置 NOT NULL 并删除旧 model 列
    with op.batch_alter_table('ai_providers') as batch:
        batch.alter_column('models', nullable=False)
        batch.drop_column('model')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ai_providers') as batch:
        batch.add_column(sa.Column('model', sa.String(length=64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, models FROM ai_providers")).fetchall()
    for row_id, models in rows:
        try:
            first = json.loads(models or "[]")[0]
        except (TypeError, ValueError, IndexError):
            first = ""
        bind.execute(
            sa.text("UPDATE ai_providers SET model = :m WHERE id = :id"),
            {"m": first, "id": row_id},
        )

    with op.batch_alter_table('ai_providers') as batch:
        batch.alter_column('model', nullable=False)
        batch.drop_column('models')
