"""审计装饰器

核心机制：动态修改 wrapper 的 __signature__，向路由函数签名注入 request: Request 参数。
FastAPI 在构建路由时读取签名，发现 Request 类型注解后会自动注入 request 对象，
使得装饰器 wrapper 能从 kwargs 中获取 request，进而写入 request.state 供中间件读取。

双保险：同时将审计元数据存储为函数属性（_audit_*），供中间件在 request.state 失效时 fallback。
"""

import inspect
import time
from functools import wraps

from fastapi import HTTPException, Request


def audit(action: str, resource_type: str, resource_id_key: str | None = None):
    """审计装饰器

    用法：
        @router.post("")
        @audit(action="CREATE", resource_type="diary")
        def create_diary(body: ..., user=Depends(get_current_user), db=Depends(get_db)):
            ...

        @router.delete("/{diary_id}")
        @audit(action="DELETE", resource_type="diary", resource_id_key="diary_id")
        def delete_diary(diary_id: int, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request: Request | None = kwargs.pop("request", None)
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return func(*args, **kwargs)

            # 自动提取身份（从依赖注入的参数中）
            admin = kwargs.get("admin")
            user = kwargs.get("user")
            if admin:
                request.state.audit_admin = admin
            if user:
                request.state.audit_user = user

            # 设置元数据
            request.state.audit_action = action
            request.state.audit_resource_type = resource_type
            request.state.audit_start_time = time.time()

            # 提取 resource_id
            if resource_id_key and resource_id_key in kwargs:
                request.state.audit_resource_id = str(kwargs[resource_id_key])

            try:
                result = func(*args, **kwargs)
                request.state.audit_response_success = True
                return result
            except HTTPException as e:
                request.state.audit_response_code = e.status_code
                request.state.audit_response_message = str(e.detail)
                request.state.audit_response_success = False
                raise
            except Exception:
                request.state.audit_response_code = 500
                request.state.audit_response_message = "服务器内部错误"
                request.state.audit_response_success = False
                raise

        # --- 关键：动态注入 request 参数到 wrapper 签名 ---
        # FastAPI 读取 wrapper.__signature__，发现 Request 类型注解后自动注入 request 对象。
        # 原始路由函数不需要声明 request: Request，装饰器透明处理。
        sig = inspect.signature(func)
        if "request" not in sig.parameters:
            new_params = [
                inspect.Parameter(
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Request,
                ),
                *sig.parameters.values(),
            ]
            wrapper.__signature__ = sig.replace(parameters=new_params)

        # --- 双保险：审计元数据存为函数属性，供中间件 fallback ---
        wrapper._audit_action = action
        wrapper._audit_resource_type = resource_type
        wrapper._audit_resource_id_key = resource_id_key

        return wrapper

    return decorator
