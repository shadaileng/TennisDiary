"""新增 file_bindings 业务绑定表并回填（138 文件管理重构）

Revision ID: d4e8b2f17c09
Revises: b7d41e0c9a35
Create Date: 2026-09-07 14:20:00.000000

`file_bindings` 是引用计数的唯一事实来源（替代「对 ref_count 直接自增自减」）：

- bind = 插入绑定（唯一约束保证幂等）→ ref_count +1
- unbind = 删除绑定 → ref_count -1
- rebind = 按目标集合差量同步

回填：把 users.avatar_url / gears.photo / analyses.video_url / analyses.thumb
四条主引用落成绑定，并把 files.ref_count 重置为绑定数（新语义：0=未绑定）。
JSON 字段（highlights / pose / derivatives）由扫描期的业务注册表兜底保护，
不会因 ref_count=0 被误清理。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8b2f17c09"
down_revision: Union[str, Sequence[str], None] = "b7d41e0c9a35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """建表 → 回填主引用绑定 → ref_count 重置为绑定数"""
    op.create_table(
        "file_bindings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("business_type", sa.String(length=32), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "file_id",
            "business_type",
            "business_id",
            "field",
            name="uq_file_binding_target",
        ),
    )
    op.create_index("ix_file_bindings_file_id", "file_bindings", ["file_id"])
    op.create_index("ix_file_bindings_user_id", "file_bindings", ["user_id"])
    op.create_index("ix_file_bindings_business_type", "file_bindings", ["business_type"])
    op.create_index("ix_file_bindings_business_id", "file_bindings", ["business_id"])

    bind = op.get_bind()

    backfills = [
        (
            "user",
            "avatar_url",
            """
            SELECT f.id, f.user_id, u.id, f.created_at
            FROM users u
            JOIN files f ON f.rel_path = u.avatar_url AND f.deleted_at IS NULL
            WHERE u.avatar_url IS NOT NULL AND u.avatar_url != ''
            """,
        ),
        (
            "gear",
            "photo",
            """
            SELECT f.id, f.user_id, g.id, f.created_at
            FROM gears g
            JOIN files f ON f.rel_path = g.photo AND f.deleted_at IS NULL
            WHERE g.photo IS NOT NULL AND g.photo != ''
            """,
        ),
        (
            "analysis",
            "video_url",
            """
            SELECT f.id, f.user_id, a.id, f.created_at
            FROM analyses a
            JOIN files f ON f.rel_path = a.video_url AND f.deleted_at IS NULL
            WHERE a.video_url IS NOT NULL AND a.video_url != ''
            """,
        ),
        (
            "analysis",
            "thumb",
            """
            SELECT f.id, f.user_id, a.id, f.created_at
            FROM analyses a
            JOIN files f ON f.rel_path = a.thumb AND f.deleted_at IS NULL
            WHERE a.thumb IS NOT NULL AND a.thumb != ''
            """,
        ),
    ]

    for business_type, field, select_sql in backfills:
        rows = bind.execute(sa.text(select_sql)).fetchall()
        for file_id, user_id, business_id, created_at in rows:
            bind.execute(
                sa.text(
                    """
                    INSERT OR IGNORE INTO file_bindings
                        (file_id, user_id, business_type, business_id, field, created_at)
                    VALUES (:file_id, :user_id, :business_type, :business_id, :field, :created_at)
                    """
                ),
                {
                    "file_id": file_id,
                    "user_id": user_id,
                    "business_type": business_type,
                    "business_id": business_id,
                    "field": field,
                    "created_at": created_at,
                },
            )

    bind.execute(
        sa.text(
            """
            UPDATE files
            SET ref_count = (
                SELECT COUNT(*) FROM file_bindings WHERE file_bindings.file_id = files.id
            )
            """
        )
    )


def downgrade() -> None:
    """删表（ref_count 保留为绑定数，语义退化为普通计数）"""
    op.drop_index("ix_file_bindings_business_id", table_name="file_bindings")
    op.drop_index("ix_file_bindings_business_type", table_name="file_bindings")
    op.drop_index("ix_file_bindings_user_id", table_name="file_bindings")
    op.drop_index("ix_file_bindings_file_id", table_name="file_bindings")
    op.drop_table("file_bindings")
