"""审计日志写入服务"""

import json
from datetime import datetime, timezone

from fastapi import Request

from app.core.audit_db import AuditSession
from app.models.audit_log import AuditLog

_SENSITIVE_FIELDS = {"password", "new_password", "api_key", "token"}


def _mask_body(body: dict | None) -> dict | None:
    """请求体敏感字段脱敏"""
    if not body:
        return None
    masked = {}
    for k, v in body.items():
        if k in _SENSITIVE_FIELDS:
            if isinstance(v, str) and v.startswith("sk-") and len(v) > 4:
                masked[k] = f"sk-****{v[-4:]}"
            else:
                masked[k] = "***"
        else:
            masked[k] = v
    return masked


def log_action(
    *,
    request: Request,
    admin=None,
    user=None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    description: str = "",
    request_body: dict | None = None,
    request_path: str = "",
    request_method: str = "",
    response_code: int = 0,
    response_success: bool = True,
    response_message: str = "",
    duration_ms: float = 0.0,
) -> None:
    """记录审计日志（独立事务，不影响业务）"""
    try:
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "")[:256]

        log = AuditLog(
            source="admin" if admin else "user",
            admin_id=admin.id if admin else None,
            user_id=user.id if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            request_body=json.dumps(_mask_body(request_body), ensure_ascii=False)
            if request_body
            else None,
            request_path=request_path,
            request_method=request_method,
            response_code=response_code,
            response_success=response_success,
            response_message=response_message,
            duration_ms=duration_ms,
            ip_address=ip,
            user_agent=ua,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        session = AuditSession()
        try:
            session.add(log)
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
        finally:
            session.close()
    except Exception:  # noqa: BLE001
        pass  # 审计本身异常静默，绝不影响业务
