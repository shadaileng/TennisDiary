import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ==================== 用户 ====================


class UserResponse(BaseModel):
    id: int
    openid: str
    nickname: str = ""
    avatar_url: str = ""
    gender: int = 0  # 0=保密 1=男 2=女
    birthday: str = ""  # YYYY-MM-DD

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """用户资料更新 — 所有字段可选，仅更新传入的字段"""

    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=512)
    gender: int | None = Field(default=None, ge=0, le=2)
    birthday: str | None = Field(default=None, max_length=10)


# ==================== 认证 ====================


class LoginRequest(BaseModel):
    code: str  # wx.login 返回的临时 code


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(TokenResponse):
    user: UserResponse
    is_new: bool = False


class UserUpdateResponse(BaseModel):
    user: UserResponse


# ==================== 日记 ====================


class CostItem(BaseModel):
    name: str
    amount: float


class GearUse(BaseModel):
    name: str
    feeling: str


class DiaryCreate(BaseModel):
    date: str  # YYYY-MM-DD
    time: str = ""
    type: str = "训练"  # 训练/比赛/发球机/发球练习
    duration: int = 0
    intensity: int = Field(default=3, ge=1, le=5)
    mood: int = Field(default=3, ge=1, le=5)
    costs: list[CostItem] = []
    gears: list[GearUse] = []
    notes: str = ""


class DiaryUpdate(BaseModel):
    """日记更新 — 所有字段可选，仅更新传入的字段"""

    date: str | None = None
    time: str | None = None
    type: str | None = None
    duration: int | None = None
    intensity: int | None = Field(default=None, ge=1, le=5)
    mood: int | None = Field(default=None, ge=1, le=5)
    costs: list[CostItem] | None = None
    gears: list[GearUse] | None = None
    notes: str | None = None


class DiaryResponse(DiaryCreate):
    id: int
    user_id: int
    created_at: float
    created_at_datetime: str | None = None

    model_config = {"from_attributes": True}


# ==================== 装备 ====================


class GearCreate(BaseModel):
    category: str = ""
    name: str = ""
    buy_date: str = ""
    price: float = 0
    feeling: str = ""
    photo: str = ""


class GearUpdate(BaseModel):
    """装备更新 — 所有字段可选"""

    category: str | None = None
    name: str | None = None
    buy_date: str | None = None
    price: float | None = None
    feeling: str | None = None
    photo: str | None = None


class GearResponse(GearCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


# ==================== 体重 ====================


class WeightCreate(BaseModel):
    date: str
    weight: float
    bust: float | None = None
    waist: float | None = None
    hip: float | None = None


class WeightResponse(WeightCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


# ==================== 打卡 ====================


class CheckinCreate(BaseModel):
    course_id: str
    date: str


class CheckinResponse(CheckinCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


# ==================== 分析 ====================


class AnalyzeRequest(BaseModel):
    """AI 分析请求：frames 为按时间顺序抽取的关键帧（base64/dataURL）"""

    frames: list[str] = Field(min_length=1, description="关键帧 base64/dataURL 数组")
    kind: str = Field(default="综合", description="击球类型（正手/反手/发球/截击/高压/综合）")
    mode: Literal["single", "full"] = Field(
        default="single", description="single=单次挥拍 / full=综合分析"
    )


class DimensionScore(BaseModel):
    name: str
    score: float
    comment: str


class ImprovementItem(BaseModel):
    issue: str
    advice: str


class AnalysisReportSchema(BaseModel):
    score: float
    summary: str
    ntrp: str | None = None
    dimensions: list[DimensionScore] = []
    rhythm: str = ""
    strengths: list[str] = []
    improvements: list[ImprovementItem] = []


class AnalysisCreate(BaseModel):
    date: str
    kind: str = "综合"
    mode: str = "single"
    score: float = 0
    summary: str = ""
    ntrp: str | None = None
    report: AnalysisReportSchema | None = None
    thumb: str | None = None
    highlights: list[str] | None = None
    video_url: str | None = None
    pose: dict | None = None


class AnalysisResponse(AnalysisCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


# ==================== AI 分享文案 ====================


class CaptionRequest(BaseModel):
    """AI 分享文案生成请求：只传模板类型与风格，业务数据由后端按当前用户查库"""

    template: Literal["月度战报", "今日日记", "技术评分"]
    style: Literal["活泼", "简洁", "专业"] = "活泼"
    text: str = Field(default="", description="当前 textarea 内容，AI 在此基础上润色")


class CaptionResponse(BaseModel):
    caption: str


# ==================== 发布 ====================


class PostCreate(BaseModel):
    date: str
    platform: str = "小红书"
    title: str = ""
    content: str = ""
    status: str = "草稿"


class PostResponse(PostCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


# ==================== 统计 ====================


class StatsResponse(BaseModel):
    total_sessions: int = 0
    total_duration: int = 0  # 分钟
    avg_intensity: float = 0
    avg_mood: float = 0
    total_cost: float = 0
    total_gears: int = 0
    total_analyses: int = 0
    avg_score: float = 0


# ==================== 事件日志 ====================


class EventLogCreate(BaseModel):
    level: str = Field(..., pattern="^(info|warn|error|fatal)$")
    type: str = "custom"
    trace_id: str | None = None
    action: str | None = None
    message: str
    stack: str = ""
    page: str = ""
    extra: dict = {}
    device_info: dict = {}
    client_time: int | None = None


class EventLogResponse(BaseModel):
    id: int
    user_id: int | None
    level: str
    type: str = "custom"
    trace_id: str | None
    action: str | None
    message: str
    stack: str = ""
    page: str = ""
    extra: dict = {}
    device_info: dict = {}
    client_time: int | None
    created_at: float

    model_config = {"from_attributes": True}

    @field_validator("extra", "device_info", mode="before")
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v or {}

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, datetime):
            return v.timestamp()
        return v


# ==================== 通用 ====================


class MessageResponse(BaseModel):
    message: str
