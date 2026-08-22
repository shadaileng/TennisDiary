"""管理员认证测试"""


def test_admin_login_success(client, test_admin, test_roles):
    """测试管理员登录成功，且响应包含完整的 role_id/role 信息"""
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["admin"]["username"] == "testadmin"
    assert data["admin"]["role_id"] == test_roles["superadmin"].id
    assert data["admin"]["role"]["code"] == "superadmin"
    assert data["admin"]["role"]["id"] == test_roles["superadmin"].id


def test_admin_login_wrong_password(client, test_admin):
    """测试错误密码登录"""
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "testadmin", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_get_admin_info(auth_client, test_roles):
    """测试获取管理员信息，且响应包含完整的 role_id/role 信息"""
    response = auth_client.get("/api/admin/auth/me")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "testadmin"
    assert data["role_id"] == test_roles["superadmin"].id
    assert data["role"]["code"] == "superadmin"
    assert data["role"]["id"] == test_roles["superadmin"].id
