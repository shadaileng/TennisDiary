"""GET/POST/PUT/DELETE /api/gears 装备接口测试"""

from app.models.gear import Gear


def _seed_gear(test_db, user_id: int = 1, **kwargs) -> Gear:
    defaults = dict(
        user_id=user_id,
        category="球拍",
        name="Wilson Pro Staff",
        buy_date="2026-01-15",
        price=1200.0,
        feeling="手感很好",
        photo="uploads/images/photo.jpg",
        created_at=1754400000.0,
    )
    defaults.update(kwargs)
    gear = Gear(**defaults)
    test_db.add(gear)
    test_db.commit()
    test_db.refresh(gear)
    return gear


class TestCreateGear:
    def test_create_gear(self, auth_client):
        payload = {
            "category": "球线",
            "name": "Luxilon",
            "buy_date": "2026-02-01",
            "price": 200.0,
            "feeling": "弹性好",
            "photo": "uploads/images/line.jpg",
        }
        resp = auth_client.post("/api/gears", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["user_id"] == 1
        assert data["category"] == "球线"
        assert data["price"] == 200.0
        assert data["created_at"] > 0

    def test_create_gear_requires_auth(self, client):
        resp = client.post("/api/gears", json={"name": "test"})
        assert resp.status_code in (401, 403)

    def test_create_gear_defaults(self, auth_client):
        resp = auth_client.post("/api/gears", json={"name": "基础球"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == ""
        assert data["price"] == 0


class TestListGears:
    def test_list_returns_only_own(self, auth_client, test_db):
        _seed_gear(test_db, user_id=1)
        _seed_gear(test_db, user_id=2)

        resp = auth_client.get("/api/gears")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 1

    def test_list_ordered_by_id_desc(self, auth_client, test_db):
        _seed_gear(test_db, user_id=1, name="A")
        _seed_gear(test_db, user_id=1, name="B")
        _seed_gear(test_db, user_id=1, name="C")

        resp = auth_client.get("/api/gears")
        assert resp.status_code == 200
        ids = [g["id"] for g in resp.json()]
        assert ids == sorted(ids, reverse=True)


class TestGetGear:
    def test_get_by_id(self, auth_client, test_db):
        gear = _seed_gear(test_db, user_id=1)
        resp = auth_client.get(f"/api/gears/{gear.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == gear.id
        assert data["name"] == "Wilson Pro Staff"

    def test_get_other_user_gear_404(self, auth_client, test_db):
        gear = _seed_gear(test_db, user_id=2)
        resp = auth_client.get(f"/api/gears/{gear.id}")
        assert resp.status_code == 404


class TestUpdateGear:
    def test_update_partial(self, auth_client, test_db):
        gear = _seed_gear(test_db, user_id=1)
        resp = auth_client.put(
            f"/api/gears/{gear.id}", json={"price": 1500.0, "feeling": "更顺手了"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 1500.0
        assert data["feeling"] == "更顺手了"
        # 未更新字段保持不变
        assert data["name"] == "Wilson Pro Staff"

    def test_update_other_user_gear_404(self, auth_client, test_db):
        gear = _seed_gear(test_db, user_id=2)
        resp = auth_client.put(f"/api/gears/{gear.id}", json={"price": 1500.0})
        assert resp.status_code == 404


class TestDeleteGear:
    def test_delete_gear(self, auth_client, test_db):
        gear = _seed_gear(test_db, user_id=1)
        resp = auth_client.delete(f"/api/gears/{gear.id}")
        assert resp.status_code in (200, 204)
        resp2 = auth_client.get(f"/api/gears/{gear.id}")
        assert resp2.status_code == 404

    def test_delete_other_user_gear_404(self, auth_client, test_db):
        gear = _seed_gear(test_db, user_id=2)
        resp = auth_client.delete(f"/api/gears/{gear.id}")
        assert resp.status_code == 404
