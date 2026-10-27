"""备份记录模型（PG 主库版）。

备份/恢复记录（backup_logs）直接存储在 PG 主库中，与业务数据统一管理，
避免 SQLite 文件锁问题，并支持高并发和异步操作。
"""

from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.orm import declarative_base

from app.core.database import Base


class BackupLog(Base):
    __tablename__ = "backup_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 完整文件名（backup_*.tar.gz / pre_restore_*.tar.gz / upload_*.tar.gz / *.db）
    name = Column(String(256), nullable=False, unique=True, index=True)
    # 文件字节大小
    size = Column(Integer, nullable=False, default=0)
    # manual=手动备份 / pre_restore=恢复前兜底 / upload=上传备份
    type = Column(String(16), nullable=False, default="manual", index=True)
    # created=正常 / restored=已用于恢复 / deleted=已删除(软删)
    status = Column(String(16), nullable=False, default="created", index=True)
    # 备注（如上传来源、恢复目标）
    note = Column(String(256), default="")
    # 操作该记录的管理员 id（创建者）
    created_by = Column(Integer, nullable=True)
    # 最近一次恢复操作的管理员 id
    restored_by = Column(Integer, nullable=True)
    restored_at = Column(DateTime, nullable=True)
    # 关联字段：被恢复的备份记录，指向恢复前生成的兜底备份记录 id
    restored_from_id = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # 软删除标记
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 复合索引提升查询性能
    __table_args__ = (
        Index("ix_backup_logs_type_status", "type", "status"),
    )
