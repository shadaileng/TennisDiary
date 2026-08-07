"""数据模型集中导出。

集中导入全部模型，确保 SQLAlchemy `Base.metadata` 在 Alembic 迁移
（`alembic/env.py` 中 `from app.models import *`）与运行时均能发现所有表。
"""

from app.models.analysis import Analysis
from app.models.checkin import Checkin
from app.models.diary import Diary
from app.models.gear import Gear
from app.models.post import Post
from app.models.user import User
from app.models.weight import WeightRecord

__all__ = [
    "Analysis",
    "Checkin",
    "Diary",
    "Gear",
    "Post",
    "User",
    "WeightRecord",
]
