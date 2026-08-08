"""统一API响应格式"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""

    code: int = 0
    message: str = "ok"
    success: bool = True
    data: T | None = None


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
    NOT_FOUND = 30001
    ALREADY_EXISTS = 30002

    # 数据库 40000-49999
    DB_ERROR = 40001
    DUPLICATE_KEY = 40002

    # 服务器 50000-59999
    INTERNAL_ERROR = 50001
