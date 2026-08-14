"""数据模型集中导出。

集中导入全部模型，确保 SQLAlchemy `Base.metadata` 在 Alembic 迁移
（`alembic/env.py` 中 `from app.models import *`）与运行时均能发现所有表。
"""

from app.models.admin import Admin
from app.models.ai_provider import AiProvider
from app.models.analysis import Analysis
from app.models.checkin import Checkin
from app.models.diary import Diary
from app.models.event_log import EventLog
from app.models.gear import Gear
from app.models.post import Post
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.models.user import User
from app.models.weight import WeightRecord

__all__ = [
    "Admin",
    "AiProvider",
    "Analysis",
    "Checkin",
    "Diary",
    "EventLog",
    "Gear",
    "Post",
    "Role",
    "SystemConfig",
    "User",
    "WeightRecord",
]
