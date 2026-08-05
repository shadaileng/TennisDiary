from pydantic import BaseModel
from typing import Optional


# ==================== 认证 ====================

class LoginRequest(BaseModel):
    code: str  # wx.login 返回的临时 code


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    intensity: int = 3  # 1-5
    mood: int = 3  # 1-5
    costs: list[CostItem] = []
    gears: list[GearUse] = []
    notes: str = ""


class DiaryUpdate(DiaryCreate):
    pass


class DiaryResponse(DiaryCreate):
    id: int
    user_id: int
    created_at: float
    created_at_datetime: Optional[str] = None

    model_config = {"from_attributes": True}


# ==================== 装备 ====================

class GearCreate(BaseModel):
    category: str = ""
    name: str = ""
    buy_date: str = ""
    price: float = 0
    feeling: str = ""
    photo: str = ""


class GearUpdate(GearCreate):
    pass


class GearResponse(GearCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


# ==================== 体重 ====================

class WeightCreate(BaseModel):
    date: str
    weight: float
    bust: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None


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
    ntrp: Optional[str] = None
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
    ntrp: Optional[str] = None
    report: Optional[AnalysisReportSchema] = None
    thumb: Optional[str] = None
    highlights: Optional[list[str]] = None


class AnalysisResponse(AnalysisCreate):
    id: int
    user_id: int
    created_at: float

    model_config = {"from_attributes": True}


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


# ==================== 通用 ====================

class MessageResponse(BaseModel):
    message: str
