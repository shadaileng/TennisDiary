"""统计汇总相关路由"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.diary import Diary
from app.models.gear import Gear
from app.models.user import User
from app.schemas.schemas import StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户统计数据汇总"""
    user_id = current_user.id

    total_sessions = db.scalar(select(func.count(Diary.id)).where(Diary.user_id == user_id))
    total_duration = (
        db.scalar(
            select(func.coalesce(func.sum(Diary.duration), 0)).where(Diary.user_id == user_id)
        )
        or 0
    )
    avg_intensity = (
        db.scalar(select(func.avg(Diary.intensity)).where(Diary.user_id == user_id)) or 0.0
    )
    avg_mood = db.scalar(select(func.avg(Diary.mood)).where(Diary.user_id == user_id)) or 0.0

    total_gears = db.scalar(select(func.count(Gear.id)).where(Gear.user_id == user_id))
    total_analyses = db.scalar(select(func.count(Analysis.id)).where(Analysis.user_id == user_id))
    avg_score = (
        db.scalar(select(func.avg(Analysis.score)).where(Analysis.user_id == user_id)) or 0.0
    )

    # total_cost 需解析每条日记的 costs JSON 文本后累加
    total_cost = 0.0
    if total_sessions:
        diaries = db.scalars(select(Diary).where(Diary.user_id == user_id)).all()
        for d in diaries:
            for c in json.loads(d.costs) if d.costs else []:
                total_cost += float(c.get("amount", 0))

    return StatsResponse(
        total_sessions=total_sessions or 0,
        total_duration=int(total_duration),
        avg_intensity=round(float(avg_intensity), 2),
        avg_mood=round(float(avg_mood), 2),
        total_cost=round(total_cost, 2),
        total_gears=total_gears or 0,
        total_analyses=total_analyses or 0,
        avg_score=round(float(avg_score), 2),
    )
