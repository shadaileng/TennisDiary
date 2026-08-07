"""POST /api/auth/login 微信登录接口测试"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.auth import get_current_user
from app.models.user import User


class TestAuthLogin:
    """测试 /api/auth/login 接口"""

    def test_login_with_valid_code_creates_user(self, client, test_db):
        """首次登录：code 有效 → 自动创建用户 + 返回 JWT 与 user"""
        with patch(
            "app.routers.auth.code_to_openid", new=AsyncMock(return_value="wx_openid_new_user_001")
        ):
            response = client.post("/api/auth/login", json={"code": "valid_code_001"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # 新增：返回 user 与 is_new
        assert data["is_new"] is True
        assert data["user"]["openid"] == "wx_openid_new_user_001"
        assert data["user"]["nickname"] == ""

        # 确认用户已写入数据库
        from app.models.user import User

        user = test_db.query(User).filter_by(openid="wx_openid_new_user_001").first()
        assert user is not None

    def test_login_returns_existing_user(self, client, test_db):
        """已注册用户再次登录：返回已有用户信息，不重复创建"""
        from app.models.user import User

        existing = User(openid="wx_openid_existing", nickname="老用户")
        test_db.add(existing)
        test_db.commit()

        with patch(
            "app.routers.auth.code_to_openid", new=AsyncMock(return_value="wx_openid_existing")
        ):
            response = client.post("/api/auth/login", json={"code": "valid_code_002"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # 老用户 is_new=False，user 带已有昵称
        assert data["is_new"] is False
        assert data["user"]["nickname"] == "老用户"

        users = test_db.query(User).filter_by(openid="wx_openid_existing").all()
        assert len(users) == 1
        assert users[0].nickname == "老用户"

    def test_login_without_code_returns_422(self, client):
        """缺少 code 字段 → 422 Validation Error"""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_login_with_invalid_code_returns_401(self, client):
        """微信返回错误（如无效 code）→ 401"""
        with patch(
            "app.routers.auth.code_to_openid",
            new=AsyncMock(side_effect=ValueError("微信登录失败: invalid code (code: 40029)")),
        ):
            response = client.post("/api/auth/login", json={"code": "invalid_code"})

        assert response.status_code == 401

    def test_login_when_wx_api_unreachable_returns_502(self, client):
        """微信 API 网络异常 → 502"""
        with patch(
            "app.routers.auth.code_to_openid",
            new=AsyncMock(side_effect=RuntimeError("微信 API 调用失败: Connection timeout")),
        ):
            response = client.post("/api/auth/login", json={"code": "any_code"})

        assert response.status_code == 502


class TestAuthMe:
    """测试 /api/auth/me 获取当前用户信息接口"""

    def test_get_me_with_valid_token(self, auth_client):
        """有效 token → 返回用户信息"""
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["nickname"] == "测试用户"

    def test_get_me_without_token_returns_401_or_403(self, client):
        """无 token → 401 或 403"""
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_get_me_with_invalid_token_returns_401(self, client):
        """无效 token → 401"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestUpdateMe:
    """测试 PUT /api/auth/me 更新用户资料接口"""

    @pytest.fixture
    def update_me_client(self, client, test_db):
        """用真实 ORM User 覆盖 get_current_user，使 commit/refresh 生效"""
        user = User(openid="wx_update_me", nickname="原昵称")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        def override_get_current_user():
            return user

        from app.main import app

        app.dependency_overrides[get_current_user] = override_get_current_user
        yield user
        app.dependency_overrides.clear()

    def test_update_me_nickname(self, update_me_client, client, test_db):
        """更新昵称 → 返回最新 user"""
        response = client.put("/api/auth/me", json={"nickname": "新昵称"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["nickname"] == "新昵称"
        assert data["user"]["id"] == update_me_client.id

        # 数据库已持久化
        user = test_db.query(User).filter_by(id=update_me_client.id).first()
        assert user.nickname == "新昵称"

    def test_update_me_partial_only_updates_provided(self, update_me_client, client):
        """只传 avatar_url 不覆盖 nickname"""
        response = client.put("/api/auth/me", json={"avatar_url": "avatars/1/abc.png"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["avatar_url"] == "avatars/1/abc.png"
        assert data["user"]["nickname"] == "原昵称"

    def test_update_me_gender_birthday(self, update_me_client, client, test_db):
        """更新性别与生日 → 持久化并返回"""
        response = client.put("/api/auth/me", json={"gender": 2, "birthday": "2000-06-15"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["gender"] == 2
        assert data["user"]["birthday"] == "2000-06-15"

        user = test_db.query(User).filter_by(id=update_me_client.id).first()
        assert user.gender == 2
        assert user.birthday == "2000-06-15"

    def test_update_me_invalid_gender_returns_422(self, update_me_client, client):
        """性别越界 → 422"""
        response = client.put("/api/auth/me", json={"gender": 5})
        assert response.status_code == 422

    def test_update_me_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.put("/api/auth/me", json={"nickname": "x"})
        assert response.status_code in (401, 403)
