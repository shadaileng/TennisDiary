"""备份元数据库独立连接。

备份/恢复记录（backup_records）存放在独立的 SQLite 文件 backup_meta.db 中，
与业务数据库 tennis_diary.db 完全隔离，业务库的备份与恢复都不影响它：

- 备份时 _pack_data_dir 排除 backup_meta.db，恢复时 tar.extractall 也不覆盖它，
  因此备份/恢复历史记录始终保留，纯表驱动列表始终完整。
- 独立 MetaBase / engine / Session，不掺入业务库的 Base.metadata。
- 单表、无演进，模块加载时用 create_all 幂等建表，不引入 Alembic，
  不触碰业务库的任何初始化与迁移逻辑。
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# 独立元数据库文件名：{DATA_DIR}/backup_meta.db
BACKUP_META_DB_NAME = "backup_meta.db"


def _meta_db_path() -> str:
    return os.path.join(settings.DATA_DIR, BACKUP_META_DB_NAME)


# 确保元数据库所在目录存在
db_dir = Path(_meta_db_path()).resolve().parent
os.makedirs(db_dir, exist_ok=True)

# 独立元数据库 engine
backup_meta_engine = create_engine(
    f"sqlite:///{_meta_db_path()}",
    connect_args={"check_same_thread": False},
)

# 独立 Base（仅包含备份记录相关模型）
MetaBase = declarative_base()

# 独立 Session
BackupMetaSession = sessionmaker(autocommit=False, autoflush=False, bind=backup_meta_engine)


# 模块加载时自包含建表（幂等），无需业务库初始化参与
from app.models.backup_record import BackupRecord  # noqa: E402, F401

MetaBase.metadata.create_all(bind=backup_meta_engine)


def get_backup_meta_db():
    """FastAPI 依赖：获取备份元数据库会话，请求结束后自动关闭"""
    db = BackupMetaSession()
    try:
        yield db
    finally:
        db.close()
