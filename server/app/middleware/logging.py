"""请求日志中间件

为每个HTTP请求添加source标识，实现日志分离：
- /api/admin/* → source=admin → 输出到 admin.log
- /api/* (其他) → source=user → 输出到 user.log
- /health 等 → source=app → 仅输出到 app.log
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录每个HTTP请求的方法、路径、状态码、耗时，并添加source标识"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # 根据路径判断source
        path = request.url.path
        if path.startswith("/api/admin"):
            source = "admin"
        elif path.startswith("/api"):
            source = "user"
        else:
            source = "app"

        # 绑定source到当前请求上下文
        request.state.source = source
        log = get_logger(source)

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        client_ip = request.client.host if request.client else "unknown"

        log.info(
            f"{request.method} {path} {response.status_code} {duration_ms:.1f}ms client={client_ip}"
        )

        return response
