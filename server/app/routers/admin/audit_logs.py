"""审计日志查询路由"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.audit_db import AuditSession
from app.core.auth import require_permission
from app.core.database import get_db
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.schemas.admin import AuditLogResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit-logs"])


def _parse_date_to_utc_str(date_str: str) -> str | None:
    """将日期字符串转为 UTC ISO 格式字符串用于比较"""
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            # 假设输入是东八区，转 UTC
            from datetime import timedelta

            dt = dt + timedelta(hours=8)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


@router.get("", response_model=ApiResponse[PaginatedData[AuditLogResponse]])
def list_audit_logs(
    offset: int = 0,
    limit: int = 20,
    source: str | None = None,
    admin_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    current_admin: Admin = Depends(require_permission("system:config")),
    db=Depends(get_db),
):
    """审计日志列表（分页 + 多条件筛选）"""
    audit_session = AuditSession()
    try:
        query = audit_session.query(AuditLog)

        if source:
            query = query.filter(AuditLog.source == source)
        if admin_id is not None:
            query = query.filter(AuditLog.admin_id == admin_id)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            utc_str = _parse_date_to_utc_str(start_date)
            if utc_str:
                query = query.filter(AuditLog.created_at >= utc_str)
        if end_date:
            utc_str = _parse_date_to_utc_str(end_date)
            if utc_str:
                query = query.filter(AuditLog.created_at <= utc_str)

        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

        if not logs:
            return ApiResponse(
                data=PaginatedData(items=[], total=total, offset=offset, limit=limit)
            )

        # 批量查询业务库获取名称（避免 N+1）
        from app.models.admin import Admin as AdminModel
        from app.models.user import User as UserModel

        admin_ids = {log.admin_id for log in logs if log.admin_id}
        user_ids = {log.user_id for log in logs if log.user_id}

        admin_map = {}
        user_map = {}

        if admin_ids:
            admins = db.query(AdminModel).filter(AdminModel.id.in_(admin_ids)).all()
            admin_map = {a.id: a.username for a in admins}

        if user_ids:
            users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
            user_map = {u.id: u.nickname for u in users}

        items = []
        for log in logs:
            items.append(
                AuditLogResponse(
                    id=log.id,
                    source=log.source,
                    admin_id=log.admin_id,
                    admin_username=admin_map.get(log.admin_id) if log.admin_id else None,
                    user_id=log.user_id,
                    user_nickname=user_map.get(log.user_id) if log.user_id else None,
                    action=log.action,
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    description=log.description or "",
                    request_body=log.request_body,
                    request_path=log.request_path or "",
                    request_method=log.request_method or "",
                    response_code=log.response_code,
                    response_success=log.response_success,
                    response_message=log.response_message or "",
                    duration_ms=log.duration_ms,
                    ip_address=log.ip_address or "",
                    user_agent=log.user_agent or "",
                    created_at=log.created_at,
                )
            )

        return ApiResponse(data=PaginatedData(items=items, total=total, offset=offset, limit=limit))
    finally:
        audit_session.close()
