"""打卡相关路由：查询 / 签到"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.checkin import Checkin
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.schemas import CheckinCreate, CheckinResponse

log = get_logger("user")

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


@router.get("", response_model=ApiResponse[list[CheckinResponse]])
def list_checkins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的打卡记录列表，按 date 倒序"""
    records = (
        db.query(Checkin)
        .filter(Checkin.user_id == current_user.id)
        .order_by(Checkin.date.desc())
        .all()
    )
    return ApiResponse(data=[CheckinResponse.model_validate(r) for r in records])


@router.post("", response_model=ApiResponse[CheckinResponse], status_code=status.HTTP_200_OK)
def create_checkin(
    body: CheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """签到 — 同用户 + 同课程 + 同日期幂等，重复签到返回已有记录"""
    import time

    existing = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == current_user.id,
            Checkin.course_id == body.course_id,
            Checkin.date == body.date,
        )
        .first()
    )
    if existing is not None:
        return ApiResponse(data=CheckinResponse.model_validate(existing))

    record = Checkin(
        user_id=current_user.id,
        course_id=body.course_id,
        date=body.date,
        created_at=time.time(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log.info("打卡成功", user_id=current_user.id, course_id=body.course_id, date=body.date)
    return ApiResponse(data=CheckinResponse.model_validate(record))
