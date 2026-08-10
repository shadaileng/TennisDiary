"""管理端事件日志查询路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.event_log import EventLog
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.schemas import EventLogResponse

router = APIRouter(prefix="/api/admin/events", tags=["admin-events"])


@router.get("", response_model=ApiResponse[PaginatedData[EventLogResponse]])
def list_event_logs(
    level: str | None = Query(None, description="按级别过滤：info/warn/error/fatal"),
    type: str | None = Query(None, description="按类型过滤：network/business/crash/custom"),
    user_id: int | None = Query(None, description="按用户ID过滤"),
    trace_id: str | None = Query(None, description="按操作链路 ID 过滤"),
    action: str | None = Query(None, description="按业务动作过滤"),
    keyword: str | None = Query(None, description="关键字搜索 message"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """查询事件日志（分页，支持多条件过滤）"""
    query = db.query(EventLog)

    if level:
        query = query.filter(EventLog.level == level)
    if type:
        query = query.filter(EventLog.type == type)
    if user_id:
        query = query.filter(EventLog.user_id == user_id)
    if trace_id:
        query = query.filter(EventLog.trace_id == trace_id)
    if action:
        query = query.filter(EventLog.action == action)
    if keyword:
        query = query.filter(EventLog.message.like(f"%{keyword}%"))

    total = query.count()
    # 优先按 client_time 降序，回退到 created_at
    items = (
        query.order_by(EventLog.client_time.desc().nullslast(), EventLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ApiResponse(
        data=PaginatedData(
            items=[EventLogResponse.model_validate(e) for e in items],
            total=total,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
    )
