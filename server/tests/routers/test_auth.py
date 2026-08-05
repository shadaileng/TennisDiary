"""POST /api/auth/login 微信登录接口测试"""

from unittest.mock import AsyncMock, patch


class TestAuthLogin:
    """测试 /api/auth/login 接口"""

    def test_login_with_valid_code_creates_user(self, client, test_db):
        """首次登录：code 有效 → 自动创建用户 + 返回 JWT"""
        with patch(
            "app.routers.auth.code_to_openid", new=AsyncMock(return_value="wx_openid_new_user_001")
        ):
            response = client.post("/api/auth/login", json={"code": "valid_code_001"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

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
