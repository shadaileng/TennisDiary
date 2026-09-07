"""文件业务绑定关系表（138 文件管理重构）

记录「哪个业务记录的哪个字段引用了哪个受管文件」，是引用计数的唯一事实来源：

- `bind` = 插入一条绑定（已存在则忽略）→ `files.ref_count` +1
- `unbind` = 删除一条绑定 → `files.ref_count` -1
- `rebind` = 按目标集合做差量同步（幂等，重复调用不重复计数）

相比「直接对 ref_count 自增自减」，绑定表可以：
- 精确知道某文件被哪些业务记录引用（扫描反查归属）
- 天然幂等，无需调用方保证调用顺序
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint

from app.core.database import Base


class FileBinding(Base):
    """文件 ↔ 业务记录的绑定关系"""

    __tablename__ = "file_bindings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(
        Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, nullable=False, index=True)
    business_type = Column(String(32), nullable=False, index=True)  # user/gear/analysis/...
    business_id = Column(Integer, nullable=False, index=True)
    field = Column(String(64), default="")  # 业务字段名：avatar_url / photo / video_url / ...
    created_at = Column(Float, default=0)

    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "business_type",
            "business_id",
            "field",
            name="uq_file_binding_target",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FileBinding file_id={self.file_id} {self.business_type}:{self.business_id}"
            f".{self.field}>"
        )
