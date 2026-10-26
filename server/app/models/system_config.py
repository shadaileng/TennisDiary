"""系统动态配置覆盖模型（system_configs，只存覆盖值，env 为默认值）"""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)  # 覆盖值
    updated_by = Column(Integer, nullable=True)  # 管理员 id
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), server_default=func.now()
    )
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
