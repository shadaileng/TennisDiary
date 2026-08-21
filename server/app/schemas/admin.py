"""管理相关请求/响应模型"""

import json
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

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
    role_id: int
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
    """重置密码请求（管理员管理接口）"""

    new_password: str = Field(..., min_length=6, max_length=128)


class AdminAuthResetRequest(BaseModel):
    """通过密钥重置密码请求（忘记密码时使用）"""

    username: str = Field(..., min_length=3, max_length=64)
    reset_key: str = Field(..., min_length=1, max_length=128)
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


# ==================== 动态配置相关 ====================


class ConfigUpdateRequest(BaseModel):
    """设置配置覆盖值请求"""

    value: str = ""


class AiProviderRequest(BaseModel):
    """AI 服务商新增/编辑请求"""

    name: str
    base_url: str
    api_key: str = ""
    models: list[str] = Field(min_length=1)
    enabled: bool = True
    sort_order: int = 0


class ProviderModelsCheckRequest(BaseModel):
    """模型可用性校验请求（表单值直传，无需先保存）"""

    base_url: str = Field(min_length=1, description="服务商接口地址，如 https://api.example.com/v1")
    api_key: str = ""
    models: list[str] = Field(min_length=1, description="待校验的模型名列表")


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str


class PermissionResponse(BaseModel):
    """权限列表响应"""

    permissions: dict[str, str]  # {code: description}


# ==================== 分页相关 ====================


class PaginationParams(BaseModel):
    """分页参数"""

    offset: int = 0
    limit: int = 20


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: list[T]
    total: int
    offset: int
    limit: int


# ==================== 数据查看相关 ====================


class UserAdminResponse(BaseModel):
    """用户信息（管理端）"""

    id: int
    openid: str  # 管理端可查看openid
    nickname: str
    avatar_url: str
    gender: int
    birthday: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DiaryAdminResponse(BaseModel):
    """日记信息（管理端）"""

    id: int
    user_id: int
    date: str
    time: str
    type: str
    duration: int
    intensity: int
    mood: int
    costs: str  # JSON字符串
    gears: str  # JSON字符串
    notes: str
    created_at: float
    user: dict | None = None

    model_config = {"from_attributes": True}


class GearAdminResponse(BaseModel):
    """装备信息（管理端）"""

    id: int
    user_id: int
    category: str
    name: str
    buy_date: str
    price: float
    feeling: str
    photo: str
    created_at: float
    user: dict | None = None

    model_config = {"from_attributes": True}


class WeightAdminResponse(BaseModel):
    """体重记录（管理端）"""

    id: int
    user_id: int
    date: str
    weight: float
    bust: float | None = None
    waist: float | None = None
    hip: float | None = None
    created_at: float
    user: dict | None = None

    model_config = {"from_attributes": True}


class CheckinAdminResponse(BaseModel):
    """打卡记录（管理端）"""

    id: int
    user_id: int
    course_id: str
    date: str
    created_at: float
    user: dict | None = None

    model_config = {"from_attributes": True}


class AnalysisAdminResponse(BaseModel):
    """分析报告（管理端）"""

    id: int
    user_id: int
    date: str
    kind: str
    mode: str
    score: float
    summary: str
    ntrp: str | None = None
    thumb: str | None = None  # 封面帧路径（列表缩略图用，避免列表解析大 JSON）
    created_at: float
    user: dict | None = None

    model_config = {"from_attributes": True}


class AnalysisDetailAdminResponse(AnalysisAdminResponse):
    """分析报告详情（管理端，含完整六维报告）"""

    report: dict | None = None  # 后端 json.loads(report) 后返回结构化对象
    highlights: list[str] | None = None  # 高光帧路径数组
    video_url: str | None = None  # 视频文件相对路径
    pose: dict | None = None  # 姿态分析结果（三角度/骨架帧/骨架视频）


class PostAdminResponse(BaseModel):
    """发布记录（管理端）"""

    id: int
    user_id: int
    date: str
    platform: str
    title: str
    content: str
    status: str
    created_at: float
    user: dict | None = None

    model_config = {"from_attributes": True}


# ==================== 审计日志相关 ====================


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    id: int
    source: str
    admin_id: int | None = None
    admin_username: str | None = None
    user_id: int | None = None
    user_nickname: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    description: str
    request_body: str | None = None
    request_path: str = ""
    request_method: str = ""
    response_code: int
    response_success: bool
    response_message: str
    duration_ms: float
    ip_address: str
    user_agent: str
    created_at: str
