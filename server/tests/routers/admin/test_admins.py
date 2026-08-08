"""管理员管理测试"""


def test_list_admins(auth_client):
    """测试管理员列表"""
    response = auth_client.get("/api/admin/admins")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1


def test_create_admin(auth_client, test_roles):
    """测试创建管理员"""
    response = auth_client.post(
        "/api/admin/admins",
        json={
            "username": "newadmin",
            "password": "newpass123",
            "nickname": "新管理员",
            "role_id": test_roles["admin"].id,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "newadmin"
    assert data["role"]["code"] == "admin"


def test_create_admin_duplicate(auth_client, test_roles):
    """测试重复用户名"""
    response = auth_client.post(
        "/api/admin/admins",
        json={
            "username": "testadmin",
            "password": "pass123",
            "role_id": test_roles["admin"].id,
        },
    )
    assert response.status_code == 400


def test_reset_password(auth_client, test_admin):
    """测试重置密码"""
    response = auth_client.put(
        f"/api/admin/admins/{test_admin.id}/password",
        json={"new_password": "newpassword123"},
    )
    assert response.status_code == 200


def test_toggle_status(auth_client, test_roles):
    """测试启用/禁用"""
    # 先创建一个新管理员用于测试
    create_response = auth_client.post(
        "/api/admin/admins",
        json={
            "username": "toggleadmin",
            "password": "togglepass123",
            "nickname": "切换状态管理员",
            "role_id": test_roles["admin"].id,
        },
    )
    assert create_response.status_code == 200
    admin_id = create_response.json()["data"]["id"]

    # 测试启用/禁用
    response = auth_client.put(f"/api/admin/admins/{admin_id}/status")
    assert response.status_code == 200


def test_delete_self(auth_client, test_admin):
    """测试删除自己"""
    response = auth_client.delete(f"/api/admin/admins/{test_admin.id}")
    assert response.status_code == 400
