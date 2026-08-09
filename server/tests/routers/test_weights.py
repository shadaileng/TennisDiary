"""GET/POST/DELETE /api/weights 体重记录接口测试"""

from app.models.weight import WeightRecord


def _seed_weight(test_db, user_id: int = 1, **kwargs) -> WeightRecord:
    defaults = dict(
        user_id=user_id,
        date="2026-08-05",
        weight=70.5,
        bust=None,
        waist=None,
        hip=None,
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    record = WeightRecord(**defaults)
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


class TestCreateWeight:
    def test_create_weight(self, auth_client):
        payload = {"date": "2026-08-05", "weight": 70.5}
        resp = auth_client.post("/api/weights", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] > 0
        assert data["user_id"] == 1
        assert data["weight"] == 70.5
        assert data["created_at"] > 0

    def test_create_weight_requires_auth(self, client):
        resp = client.post("/api/weights", json={"date": "2026-08-05", "weight": 70})
        assert resp.status_code in (401, 403)

    def test_create_weight_with_measurements(self, auth_client):
        payload = {
            "date": "2026-08-05",
            "weight": 70.5,
            "bust": 95.0,
            "waist": 80.0,
            "hip": 92.0,
        }
        resp = auth_client.post("/api/weights", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["bust"] == 95.0
        assert data["waist"] == 80.0
        assert data["hip"] == 92.0


class TestListWeights:
    def test_list_returns_only_own(self, auth_client, test_db):
        _seed_weight(test_db, user_id=1)
        _seed_weight(test_db, user_id=2)

        resp = auth_client.get("/api/weights")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["user_id"] == 1

    def test_list_ordered_by_created_at_desc(self, auth_client, test_db):
        # 创建三条体重记录，显式设置递增的 created_at
        _seed_weight(test_db, user_id=1, date="2026-08-01", created_at=1000.0)
        _seed_weight(test_db, user_id=1, date="2026-08-02", created_at=2000.0)
        _seed_weight(test_db, user_id=1, date="2026-08-03", created_at=3000.0)

        resp = auth_client.get("/api/weights")
        assert resp.status_code == 200
        ids = [w["id"] for w in resp.json()["data"]]
        assert ids == [3, 2, 1]


class TestDeleteWeight:
    def test_delete_weight(self, auth_client, test_db):
        record = _seed_weight(test_db, user_id=1)
        resp = auth_client.delete(f"/api/weights/{record.id}")
        assert resp.status_code in (200, 204)

        list_resp = auth_client.get("/api/weights")
        ids = [w["id"] for w in list_resp.json()["data"]]
        assert record.id not in ids

    def test_delete_other_user_weight_404(self, auth_client, test_db):
        record = _seed_weight(test_db, user_id=2)
        resp = auth_client.delete(f"/api/weights/{record.id}")
        assert resp.status_code == 404
