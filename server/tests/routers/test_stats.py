"""GET /api/stats 统计汇总接口测试"""

import json

from app.models.analysis import Analysis
from app.models.diary import Diary
from app.models.gear import Gear


def _seed_diary(test_db, user_id=1, **kwargs) -> Diary:
    defaults = dict(
        user_id=user_id,
        date="2026-08-05",
        time="14:30",
        type="训练",
        duration=90,
        intensity=4,
        mood=5,
        costs=json.dumps([{"name": "场地费", "amount": 100.0}]),
        gears=json.dumps([{"name": "Wilson", "feeling": "不错"}]),
        notes="",
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    diary = Diary(**defaults)
    test_db.add(diary)
    test_db.commit()
    return diary


def _seed_gear(test_db, user_id=1, **kwargs) -> Gear:
    defaults = dict(
        user_id=user_id,
        category="球拍",
        name="Wilson",
        buy_date="2026-01-15",
        price=1200.0,
        feeling="",
        photo="",
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    gear = Gear(**defaults)
    test_db.add(gear)
    test_db.commit()
    return gear


def _seed_analysis(test_db, user_id=1, **kwargs) -> Analysis:
    defaults = dict(
        user_id=user_id,
        date="2026-08-05",
        kind="综合",
        mode="single",
        score=75.0,
        summary="",
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    analysis = Analysis(**defaults)
    test_db.add(analysis)
    test_db.commit()
    return analysis


class TestStats:
    def test_empty_stats(self, auth_client):
        """无数据 → 全 0"""
        resp = auth_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 0
        assert data["total_duration"] == 0
        assert data["avg_intensity"] == 0
        assert data["avg_mood"] == 0
        assert data["total_cost"] == 0
        assert data["total_gears"] == 0
        assert data["total_analyses"] == 0
        assert data["avg_score"] == 0

    def test_stats_with_diaries(self, auth_client, test_db):
        # 两条日记：duration 90+60，intensity 4/2，mood 5/3，costs 100/50
        _seed_diary(
            test_db,
            user_id=1,
            duration=90,
            intensity=4,
            mood=5,
            costs=json.dumps([{"name": "a", "amount": 100.0}]),
        )
        _seed_diary(
            test_db,
            user_id=1,
            duration=60,
            intensity=2,
            mood=3,
            costs=json.dumps([{"name": "b", "amount": 50.0}]),
        )
        resp = auth_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 2
        assert data["total_duration"] == 150
        assert data["avg_intensity"] == 3.0
        assert data["avg_mood"] == 4.0
        assert data["total_cost"] == 150.0

    def test_stats_with_gears_and_analyses(self, auth_client, test_db):
        _seed_gear(test_db, user_id=1)
        _seed_gear(test_db, user_id=1)
        _seed_analysis(test_db, user_id=1, score=80.0)
        _seed_analysis(test_db, user_id=1, score=60.0)
        resp = auth_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_gears"] == 2
        assert data["total_analyses"] == 2
        assert data["avg_score"] == 70.0

    def test_stats_only_own_data(self, auth_client, test_db):
        """他人数据不计入"""
        _seed_diary(
            test_db,
            user_id=2,
            duration=999,
            intensity=5,
            mood=5,
            costs=json.dumps([{"name": "x", "amount": 999.0}]),
        )
        _seed_gear(test_db, user_id=2)
        _seed_analysis(test_db, user_id=2, score=99.0)

        resp = auth_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 0
        assert data["total_gears"] == 0
        assert data["total_analyses"] == 0
        assert data["avg_score"] == 0

    def test_stats_requires_auth(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code in (401, 403)
