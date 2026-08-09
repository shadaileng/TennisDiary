"""小程序事件日志上报路由（公开接口，免鉴权）"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.event_log import EventLog
from app.schemas.common import ApiResponse
from app.schemas.schemas import EventLogCreate, EventLogResponse

log = get_logger("user")

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=ApiResponse[EventLogResponse])
async def create_event_log(body: EventLogCreate, db: Session = Depends(get_db)):
    """上报事件日志（小程序端调用，无需鉴权）"""
    user_id = body.extra.get("user_id")
    if user_id:
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            user_id = None

    event = EventLog(
        user_id=user_id,
        level=body.level,
        type=body.type,
        trace_id=body.trace_id,
        action=body.action,
        message=body.message,
        stack=body.stack,
        page=body.page,
        extra=json.dumps(body.extra, ensure_ascii=False),
        device_info=json.dumps(body.device_info, ensure_ascii=False),
        client_time=body.client_time,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    log.info(f"事件日志上报: {body.level} {body.type}", event_id=event.id)
    return ApiResponse(data=EventLogResponse.model_validate(event))
