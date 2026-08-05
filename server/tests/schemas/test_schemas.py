"""Pydantic Schemas 验证测试"""

import pytest
from pydantic import ValidationError

from app.schemas.schemas import (
    # Auth
    LoginRequest,
    TokenResponse,
    # Diary
    CostItem,
    GearUse,
    DiaryCreate,
    DiaryUpdate,
    DiaryResponse,
    # Gear
    GearCreate,
    GearUpdate,
    GearResponse,
    # Weight
    WeightCreate,
    WeightResponse,
    # Checkin
    CheckinCreate,
    CheckinResponse,
    # Analysis
    DimensionScore,
    ImprovementItem,
    AnalysisReportSchema,
    AnalysisCreate,
    AnalysisResponse,
    # Post
    PostCreate,
    PostResponse,
    # Stats
    StatsResponse,
    # Common
    MessageResponse,
    # User
    UserResponse,
)


# ==================== 认证 ====================

class TestLoginRequest:
    def test_valid_code(self):
        req = LoginRequest(code="abc123")
        assert req.code == "abc123"

    def test_code_is_required(self):
        with pytest.raises(ValidationError):
            LoginRequest()

    def test_empty_code_accepted(self):
        """空 code 由业务层校验，schema 层不做空判断"""
        req = LoginRequest(code="")
        assert req.code == ""


class TestTokenResponse:
    def test_default_token_type(self):
        resp = TokenResponse(access_token="token_xyz")
        assert resp.access_token == "token_xyz"
        assert resp.token_type == "bearer"


# ==================== 日记 ====================

class TestDiaryCreate:
    def test_minimal_fields(self):
        d = DiaryCreate(date="2026-08-05")
        assert d.date == "2026-08-05"
        assert d.type == "训练"
        assert d.duration == 0
        assert d.intensity == 3
        assert d.mood == 3
        assert d.costs == []
        assert d.gears == []
        assert d.notes == ""
        assert d.time == ""

    def test_full_fields(self):
        d = DiaryCreate(
            date="2026-08-05",
            time="14:30",
            type="比赛",
            duration=120,
            intensity=5,
            mood=4,
            costs=[CostItem(name="场地费", amount=100.0)],
            gears=[GearUse(name="Wilson", feeling="不错")],
            notes="正手有进步",
        )
        assert d.costs[0].name == "场地费"
        assert d.costs[0].amount == 100.0
        assert d.gears[0].name == "Wilson"

    def test_invalid_intensity_too_high(self):
        with pytest.raises(ValidationError):
            DiaryCreate(date="2026-08-05", intensity=6)

    def test_invalid_mood_too_low(self):
        with pytest.raises(ValidationError):
            DiaryCreate(date="2026-08-05", mood=0)


class TestDiaryUpdate:
    def test_partial_update(self):
        """DiaryUpdate 所有字段应可选，支持部分更新"""
        d = DiaryUpdate()
        assert d.date is None

    def test_full_update(self):
        d = DiaryUpdate(date="2026-08-06", type="发球练习", duration=60)
        assert d.date == "2026-08-06"
        assert d.type == "发球练习"
        assert d.duration == 60


class TestDiaryResponse:
    def test_from_orm_like_dict(self):
        d = DiaryResponse(
            id=1,
            user_id=1,
            date="2026-08-05",
            time="14:30",
            type="训练",
            duration=90,
            intensity=4,
            mood=5,
            costs=[],
            gears=[],
            notes="",
            created_at=1754400000.0,
        )
        assert d.id == 1
        assert d.user_id == 1


# ==================== 装备 ====================

class TestGearCreate:
    def test_defaults(self):
        g = GearCreate()
        assert g.category == ""
        assert g.name == ""
        assert g.price == 0
        assert g.photo == ""

    def test_full_fields(self):
        g = GearCreate(
            category="球拍",
            name="Wilson Pro Staff",
            buy_date="2026-01-15",
            price=1200.0,
            feeling="手感很好",
            photo="uploads/images/photo.jpg",
        )
        assert g.category == "球拍"
        assert g.price == 1200.0


class TestGearUpdate:
    def test_partial_update(self):
        g = GearUpdate()
        assert g.category is None


class TestGearResponse:
    def test_from_orm_like_dict(self):
        g = GearResponse(
            id=1,
            user_id=1,
            category="球拍",
            name="Wilson",
            buy_date="2026-01-01",
            price=800.0,
            feeling="",
            photo="",
            created_at=1754400000.0,
        )
        assert g.id == 1
        assert g.user_id == 1


# ==================== 体重 ====================

class TestWeightCreate:
    def test_minimal_fields(self):
        w = WeightCreate(date="2026-08-05", weight=70.5)
        assert w.weight == 70.5
        assert w.bust is None
        assert w.waist is None
        assert w.hip is None

    def test_with_body_measurements(self):
        w = WeightCreate(date="2026-08-05", weight=70.5, bust=95.0, waist=80.0, hip=92.0)
        assert w.bust == 95.0
        assert w.waist == 80.0
        assert w.hip == 92.0


class TestWeightResponse:
    def test_from_orm_like_dict(self):
        w = WeightResponse(
            id=1,
            user_id=1,
            date="2026-08-05",
            weight=70.5,
            bust=None,
            waist=None,
            hip=None,
            created_at=1754400000.0,
        )
        assert w.id == 1


# ==================== 打卡 ====================

class TestCheckinCreate:
    def test_valid(self):
        c = CheckinCreate(course_id="warmup_001", date="2026-08-05")
        assert c.course_id == "warmup_001"


class TestCheckinResponse:
    def test_from_orm_like_dict(self):
        c = CheckinResponse(id=1, user_id=1, course_id="warmup_001", date="2026-08-05", created_at=1754400000.0)
        assert c.id == 1


# ==================== 分析 ====================

class TestAnalysisCreate:
    def test_minimal_fields(self):
        a = AnalysisCreate(date="2026-08-05")
        assert a.kind == "综合"
        assert a.mode == "single"
        assert a.score == 0

    def test_with_report(self):
        report = AnalysisReportSchema(
            score=75.0,
            summary="总体不错",
            ntrp="3.5",
            dimensions=[
                DimensionScore(name="力量", score=80.0, comment="发力充分"),
                DimensionScore(name="旋转", score=70.0, comment="上旋不错"),
            ],
            rhythm="节奏稳定",
            strengths=["正手攻击性强"],
            improvements=[ImprovementItem(issue="反手不稳定", advice="多练反手")],
        )
        a = AnalysisCreate(date="2026-08-05", kind="正手", score=75.0, report=report)
        assert a.report is not None
        assert a.report.dimensions[0].name == "力量"
        assert a.report.ntrp == "3.5"

    def test_with_highlights(self):
        a = AnalysisCreate(
            date="2026-08-05",
            highlights=["frame1.jpg", "frame2.jpg"],
        )
        assert len(a.highlights) == 2


class TestAnalysisResponse:
    def test_from_orm_like_dict(self):
        a = AnalysisResponse(
            id=1,
            user_id=1,
            date="2026-08-05",
            kind="综合",
            mode="single",
            score=75.0,
            summary="不错",
            created_at=1754400000.0,
        )
        assert a.id == 1


# ==================== 发布 ====================

class TestPostCreate:
    def test_defaults(self):
        p = PostCreate(date="2026-08-05")
        assert p.platform == "小红书"
        assert p.status == "草稿"
        assert p.title == ""
        assert p.content == ""


class TestPostResponse:
    def test_from_orm_like_dict(self):
        p = PostResponse(
            id=1,
            user_id=1,
            date="2026-08-05",
            platform="小红书",
            title="今日训练",
            content="今天练了正手",
            status="草稿",
            created_at=1754400000.0,
        )
        assert p.id == 1


# ==================== 统计 ====================

class TestStatsResponse:
    def test_defaults(self):
        s = StatsResponse()
        assert s.total_sessions == 0
        assert s.total_duration == 0
        assert s.avg_intensity == 0
        assert s.avg_mood == 0
        assert s.total_cost == 0
        assert s.total_gears == 0
        assert s.total_analyses == 0
        assert s.avg_score == 0

    def test_with_data(self):
        s = StatsResponse(
            total_sessions=10,
            total_duration=900,
            avg_intensity=4.2,
            avg_mood=4.5,
            total_cost=800.0,
            total_gears=5,
            total_analyses=3,
            avg_score=72.5,
        )
        assert s.total_sessions == 10
        assert s.total_duration == 900


# ==================== 通用 ====================

class TestMessageResponse:
    def test_basic(self):
        m = MessageResponse(message="操作成功")
        assert m.message == "操作成功"


# ==================== 用户 ====================

class TestUserResponse:
    def test_from_orm_like_dict(self):
        u = UserResponse(
            id=1,
            openid="test_openid",
            nickname="测试用户",
            avatar_url="https://example.com/avatar.jpg",
        )
        assert u.id == 1
        assert u.openid == "test_openid"
        assert u.nickname == "测试用户"
