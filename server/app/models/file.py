"""文件管理数据模型（MD5 + 秒传 + 引用计数）"""

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from app.core.database import Base


class File(Base):
    """文件记录表：每个上传/生成的文件一条记录，支持 MD5 去重和引用计数"""

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # 所属用户
    md5 = Column(String(32), nullable=False, index=True)  # 文件 MD5，用于秒传
    original_name = Column(String(255), default="")  # 原始文件名（用户设备上的文件名）
    rel_path = Column(String(512), nullable=False, index=True)  # 相对 UPLOAD_DIR 的路径
    size_bytes = Column(Integer, default=0)  # 文件大小（字节）
    mime_type = Column(String(128), default="")  # MIME 类型
    upload_source = Column(String(32), default="")  # 来源：avatar/gear_image/video/skeleton_frame/skeleton_video/other
    business_type = Column(String(32), nullable=True, index=True)  # 业务类型：gear/analysis/user
    business_id = Column(Integer, nullable=True, index=True)  # 业务记录 ID
    ref_count = Column(Integer, default=1)  # 该物理文件被引用的次数（降为 0 可清理）
    created_at = Column(Float, default=0)  # 上传时间戳
    deleted_at = Column(Float, nullable=True, index=True)  # 软删除时间（None=未删除）

    # 唯一约束：全局不允许两个文件同名（冲突时上传端点重命名，不依赖数据库阻拦）
    # 不设 (user_id, md5) 约束：同用户重复上传同一文件应创建独立记录（秒传基础）
    __table_args__ = (
        UniqueConstraint("original_name", name="uq_files_original_name"),
    )

    def __repr__(self) -> str:
        return f"<File id={self.id} path={self.rel_path} ref_count={self.ref_count}>"
