"""GET/POST/PUT/DELETE /api/diaries 日记接口测试"""

from app.models.diary import Diary


def _seed_diary(test_db, user_id: int = 1, **kwargs) -> Diary:
    import json

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
        notes="正手有进步",
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    diary = Diary(**defaults)
    test_db.add(diary)
    test_db.commit()
    test_db.refresh(diary)
    return diary


class TestCreateDiary:
    def test_create_diary(self, auth_client):
        """带鉴权创建日记 → 返回 200 + id / user_id，costs/gears 回显"""
        payload = {
            "date": "2026-08-05",
            "time": "14:30",
            "type": "比赛",
            "duration": 120,
            "intensity": 5,
            "mood": 4,
            "costs": [{"name": "场地费", "amount": 100.0}],
            "gears": [{"name": "Wilson", "feeling": "不错"}],
            "notes": "正手有进步",
        }
        resp = auth_client.post("/api/diaries", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] > 0
        assert data["user_id"] == 1
        assert data["type"] == "比赛"
        assert data["costs"][0]["name"] == "场地费"
        assert data["gears"][0]["name"] == "Wilson"
        assert data["created_at"] > 0

    def test_create_diary_requires_auth(self, client):
        """未带 token → 401/403"""
        resp = client.post("/api/diaries", json={"date": "2026-08-05"})
        assert resp.status_code in (401, 403)

    def test_create_diary_defaults(self, auth_client):
        """仅传必填字段 → 默认 type=训练 等"""
        resp = auth_client.post("/api/diaries", json={"date": "2026-08-06"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["type"] == "训练"
        assert data["duration"] == 0
        assert data["costs"] == []
        assert data["gears"] == []


class TestListDiaries:
    def test_list_returns_only_own(self, auth_client, test_db):
        """只返回当前用户数据（mock 用户 id=1）"""
        _seed_diary(test_db, user_id=1, date="2026-08-05")
        _seed_diary(test_db, user_id=2, date="2026-08-05")  # 他人数据

        resp = auth_client.get("/api/diaries")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["user_id"] == 1

    def test_list_ordered_by_created_at_desc(self, auth_client, test_db):
        # 创建三条日记，显式设置递增的 created_at
        _seed_diary(test_db, user_id=1, date="2026-08-01", created_at=1000.0)
        _seed_diary(test_db, user_id=1, date="2026-08-02", created_at=2000.0)
        _seed_diary(test_db, user_id=1, date="2026-08-03", created_at=3000.0)

        resp = auth_client.get("/api/diaries")
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()["data"]]
        # 按 created_at 降序，所以 id 也应该是降序（因为 id 和 created_at 正相关）
        assert ids == [3, 2, 1]


class TestGetDiary:
    def test_get_by_id(self, auth_client, test_db):
        diary = _seed_diary(test_db, user_id=1)
        resp = auth_client.get(f"/api/diaries/{diary.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == diary.id
        assert data["notes"] == "正手有进步"

    def test_get_other_user_diary_404(self, auth_client, test_db):
        diary = _seed_diary(test_db, user_id=2)
        resp = auth_client.get(f"/api/diaries/{diary.id}")
        assert resp.status_code == 404


class TestUpdateDiary:
    def test_update_partial(self, auth_client, test_db):
        diary = _seed_diary(test_db, user_id=1)
        resp = auth_client.put(
            f"/api/diaries/{diary.id}", json={"duration": 150, "notes": "更新后的笔记"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["duration"] == 150
        assert data["notes"] == "更新后的笔记"
        # 未更新字段保持不变
        assert data["type"] == "训练"

    def test_update_other_user_diary_404(self, auth_client, test_db):
        diary = _seed_diary(test_db, user_id=2)
        resp = auth_client.put(f"/api/diaries/{diary.id}", json={"duration": 150})
        assert resp.status_code == 404


class TestDeleteDiary:
    def test_delete_diary(self, auth_client, test_db):
        diary = _seed_diary(test_db, user_id=1)
        resp = auth_client.delete(f"/api/diaries/{diary.id}")
        assert resp.status_code in (200, 204)
        # 再次 GET 应 404
        resp2 = auth_client.get(f"/api/diaries/{diary.id}")
        assert resp2.status_code == 404

    def test_delete_other_user_diary_404(self, auth_client, test_db):
        diary = _seed_diary(test_db, user_id=2)
        resp = auth_client.delete(f"/api/diaries/{diary.id}")
        assert resp.status_code == 404
