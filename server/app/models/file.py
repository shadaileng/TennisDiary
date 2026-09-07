"""文件管理数据模型（MD5 命名 + 同用户单记录 + 引用计数）"""

from sqlalchemy import Column, Float, Index, Integer, String, text

from app.core.database import Base


class File(Base):
    """文件记录表：受管文件一条记录，支持 MD5 去重和引用计数

    138 重构要点：
    - 物理文件名统一 `{md5}.{后缀}`，存于 `UPLOAD_DIR/{分类}/{user_id}/`
    - 同一用户同一 MD5 只保留一条**未软删**记录（部分唯一索引保证）
    - `ref_count` 语义为「业务引用次数」：登记时 0，业务绑定 +1，解绑 -1
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # 所属用户
    md5 = Column(String(32), nullable=False, index=True)  # 文件 MD5，命名与秒传依据
    original_name = Column(String(255), default="")  # 原始文件名（用户设备上的文件名）
    rel_path = Column(String(512), nullable=False, index=True)  # 相对 UPLOAD_DIR 的路径
    size_bytes = Column(Integer, default=0)  # 文件大小（字节）
    mime_type = Column(String(128), default="")  # MIME 类型
    # 来源：avatar / gear_image / video / video_frame / skeleton_video / ...
    upload_source = Column(String(32), default="")
    business_type = Column(String(32), nullable=True, index=True)  # 业务类型：gear/analysis/user
    business_id = Column(Integer, nullable=True, index=True)  # 业务记录 ID
    ref_count = Column(Integer, default=0)  # 业务引用次数（0=未绑定，可由清理任务回收）
    security_checked = Column(Integer, default=0)  # 安全检查标记：0=未检查，1=已通过
    created_at = Column(Float, default=0)  # 登记时间戳
    deleted_at = Column(Float, nullable=True, index=True)  # 软删除时间（None=未删除）

    # 138：同用户同 MD5 只允许一条有效记录（软删行被排除，可再次上传重建）
    # 原 uq_files_original_name 全局同名约束已移除：MD5 命名后跨用户必然同名
    __table_args__ = (
        Index(
            "uq_files_user_md5_active",
            "user_id",
            "md5",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<File id={self.id} path={self.rel_path} ref_count={self.ref_count}>"
