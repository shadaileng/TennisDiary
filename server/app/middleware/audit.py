"""审计中间件 - 自动审计所有写操作

读取顺序：
1. request.state（装饰器直接写入，主路径）
2. request.scope["endpoint"] 函数属性（装饰器 fallback，兜底）
3. HTTP method 默认值（未装饰的路由，如 OPTIONS 预检）
"""

import json
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.audit_service import log_action


class AuditMiddleware(BaseHTTPMiddleware):
    """自动审计所有写操作（POST/PUT/DELETE）

    职责：
    - 自动捕获 method、path、status_code、IP、UA、耗时
    - 自动缓存并解析请求体
    - 从 request.state 读取装饰器设置的审计元数据
    - 兜底：从路由函数属性（_audit_*）读取元数据
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 只审计写操作
        if request.method not in ("POST", "PUT", "DELETE"):
            return await call_next(request)

        # 缓存 body（解决消费冲突）
        body_bytes = await request.body()

        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # 解析请求体
        request_body = None
        if body_bytes:
            try:
                request_body = json.loads(body_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # --- 优先从 request.state 读取（装饰器主路径）---
        action = getattr(request.state, "audit_action", None)
        resource_type = getattr(request.state, "audit_resource_type", None)
        resource_id = getattr(request.state, "audit_resource_id", None)
        admin = getattr(request.state, "audit_admin", None)
        user = getattr(request.state, "audit_user", None)

        # --- 兜底：从路由函数属性读取（装饰器 fallback）---
        if action is None:
            endpoint = request.scope.get("endpoint")
            if endpoint and hasattr(endpoint, "_audit_action"):
                action = getattr(endpoint, "_audit_action", None)
                resource_type = getattr(endpoint, "_audit_resource_type", None)
                resource_id_key = getattr(endpoint, "_audit_resource_id_key", None)
                if resource_id_key and resource_id is None:
                    path_params = request.scope.get("path_params", {})
                    resource_id = str(path_params.get(resource_id_key, ""))

        # 最终兜底：使用 HTTP method
        if action is None:
            action = request.method
        if resource_type is None:
            resource_type = "unknown"

        # 执行审计写入
        log_action(
            request=request,
            admin=admin,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_body=request_body,
            request_path=str(request.url.path),
            request_method=request.method,
            response_code=getattr(request.state, "audit_response_code", 0) or response.status_code,
            response_success=getattr(request.state, "audit_response_success", True),
            response_message=getattr(request.state, "audit_response_message", ""),
            duration_ms=duration_ms,
        )

        return response
