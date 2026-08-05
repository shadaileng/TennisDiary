"""GET/POST /api/checkin 打卡接口测试"""

from app.models.checkin import Checkin


def _seed_checkin(test_db, user_id: int = 1, **kwargs) -> Checkin:
    defaults = dict(
        user_id=user_id,
        course_id="warmup_001",
        date="2026-08-05",
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    record = Checkin(**defaults)
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


class TestCreateCheckin:
    def test_create_checkin(self, auth_client):
        payload = {"course_id": "warmup_001", "date": "2026-08-05"}
        resp = auth_client.post("/api/checkin", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["user_id"] == 1
        assert data["course_id"] == "warmup_001"
        assert data["date"] == "2026-08-05"
        assert data["created_at"] > 0

    def test_create_checkin_requires_auth(self, client):
        resp = client.post("/api/checkin", json={"course_id": "c1", "date": "2026-08-05"})
        assert resp.status_code in (401, 403)

    def test_duplicate_checkin_idempotent(self, auth_client, test_db):
        """同 user+course+date 重复签到返回已有记录，不重复插入"""
        _seed_checkin(test_db, user_id=1, course_id="warmup_001", date="2026-08-05")
        resp = auth_client.post(
            "/api/checkin", json={"course_id": "warmup_001", "date": "2026-08-05"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0  # 返回已有记录

        # 确认库里只有一条
        count = (
            test_db.query(Checkin)
            .filter_by(user_id=1, course_id="warmup_001", date="2026-08-05")
            .count()
        )
        assert count == 1


class TestListCheckins:
    def test_list_returns_only_own(self, auth_client, test_db):
        _seed_checkin(test_db, user_id=1)
        _seed_checkin(test_db, user_id=2)

        resp = auth_client.get("/api/checkin")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 1

    def test_list_ordered_by_date_desc(self, auth_client, test_db):
        _seed_checkin(test_db, user_id=1, date="2026-08-01")
        _seed_checkin(test_db, user_id=1, date="2026-08-10")
        _seed_checkin(test_db, user_id=1, date="2026-08-05")

        resp = auth_client.get("/api/checkin")
        assert resp.status_code == 200
        dates = [c["date"] for c in resp.json()]
        assert dates == sorted(dates, reverse=True)
