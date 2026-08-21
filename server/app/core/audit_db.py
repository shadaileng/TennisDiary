"""审计日志独立数据库。

审计日志存放在独立的 SQLite 文件 audit.db 中，
与业务数据库 tennis_diary.db 完全隔离：
- 备份/恢复操作不影响审计日志
- 独立 AuditBase / engine / Session
- 单表、无演进，模块加载时 create_all 幂等建表
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

AUDIT_DB_NAME = "audit.db"


def _audit_db_path() -> str:
    return os.path.join(settings.DATA_DIR, AUDIT_DB_NAME)


# 确保目录存在
db_dir = Path(_audit_db_path()).resolve().parent
os.makedirs(db_dir, exist_ok=True)

# 独立 engine
audit_engine = create_engine(
    f"sqlite:///{_audit_db_path()}",
    connect_args={"check_same_thread": False},
)

# 独立 Base（仅审计日志模型）
AuditBase = declarative_base()

# 独立 Session
AuditSession = sessionmaker(autocommit=False, autoflush=False, bind=audit_engine)

# 幂等建表
from app.models.audit_log import AuditLog  # noqa: E402, F401

AuditBase.metadata.create_all(bind=audit_engine)
