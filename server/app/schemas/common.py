"""统一API响应格式"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.core.logging import get_logger

log = get_logger("api")

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""

    code: int = 0
    message: str = "ok"
    success: bool = True
    data: T | None = None

    def model_post_init(self, context: Any) -> None:
        """响应构造收口（147 §6.2）：两态外链改写

        任何 `ApiResponse(...)` 构造都会经过这里，用当前请求绑定的 DB 会话把
        `SYNCED` 的受管路径换成签名外链，其余原样保留（前端零改动）。
        无绑定会话或改写异常一律安全跳过，只记日志。
        """
        if self.data is None:
            return
        try:
            from app.services.storage.urls import rewrite_current_response

            rewrite_current_response(self.data)
        except Exception as exc:
            log.exception("响应外链改写失败: {}", exc)


class PaginatedData(BaseModel, Generic[T]):
    """分页数据"""

    items: list[T]
    total: int
    offset: int
    limit: int


class ErrorCode:
    """错误码定义"""

    SUCCESS = 0

    # 认证/授权 10000-19999
    UNAUTHORIZED = 10001
    TOKEN_EXPIRED = 10002
    FORBIDDEN = 10003

    # 参数校验 20000-29999
    VALIDATION_ERROR = 20001

    # 业务逻辑 30000-39999
    INVALID_REQUEST = 30000
    NOT_FOUND = 30001
    ALREADY_EXISTS = 30002

    # 数据库 40000-49999
    DB_ERROR = 40001
    DUPLICATE_KEY = 40002

    # 服务器 50000-59999
    INTERNAL_ERROR = 50001
