"""管理员认证测试"""


def test_admin_login_success(client, test_admin):
    """测试管理员登录成功"""
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["admin"]["username"] == "testadmin"
    assert "role" in data["admin"]


def test_admin_login_wrong_password(client, test_admin):
    """测试错误密码登录"""
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "testadmin", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_get_admin_info(auth_client):
    """测试获取管理员信息"""
    response = auth_client.get("/api/admin/auth/me")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "testadmin"
    assert "role" in data
