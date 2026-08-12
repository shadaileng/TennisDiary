"""备份记录模型（独立元数据库 backup_meta.db）。

记录每次备份/恢复/上传/删除操作与备份文件元信息。
该表不参与业务数据库的备份与恢复，独立持久化，用于审计与列表展示。
"""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.core.backup_meta import MetaBase


class BackupRecord(MetaBase):
    __tablename__ = "backup_records"

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
