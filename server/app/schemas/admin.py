"""管理相关请求/响应模型"""

import json
from datetime import datetime

from pydantic import BaseModel, Field

# ==================== 角色相关 ====================


class RoleCreateRequest(BaseModel):
    """创建角色请求"""

    name: str = Field(..., min_length=2, max_length=32)
    code: str = Field(..., min_length=2, max_length=32)
    description: str = ""
    permissions: list[str] = []


class RoleUpdateRequest(BaseModel):
    """编辑角色请求"""

    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class RoleResponse(BaseModel):
    """角色响应"""

    id: int
    name: str
    code: str
    description: str
    permissions: list[str]
    is_system: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建"""
        perms = json.loads(obj.permissions) if obj.permissions else []
        return cls(
            id=obj.id,
            name=obj.name,
            code=obj.code,
            description=obj.description or "",
            permissions=perms,
            is_system=obj.is_system,
            created_at=obj.created_at,
        )


class RoleListResponse(BaseModel):
    """角色列表响应"""

    items: list[RoleResponse]
    total: int


# ==================== 管理员相关 ====================


class AdminLoginRequest(BaseModel):
    """管理员登录请求"""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class AdminResponse(BaseModel):
    """管理员信息响应"""

    id: int
    username: str
    nickname: str
    role: RoleResponse
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminTokenResponse(BaseModel):
    """管理员登录响应"""

    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse


class AdminCreateRequest(BaseModel):
    """创建管理员请求"""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    nickname: str = ""
    role_id: int


class AdminUpdateRequest(BaseModel):
    """编辑管理员请求"""

    nickname: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class AdminResetPasswordRequest(BaseModel):
    """重置密码请求"""

    new_password: str = Field(..., min_length=6, max_length=128)


class AdminPasswordUpdate(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminListResponse(BaseModel):
    """管理员列表响应"""

    items: list[AdminResponse]
    total: int
    offset: int
    limit: int


# ==================== 通用 ====================


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str


class PermissionResponse(BaseModel):
    """权限列表响应"""

    permissions: dict[str, str]  # {code: description}
