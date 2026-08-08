"""角色管理测试"""


def test_list_roles(auth_client):
    """测试角色列表"""
    response = auth_client.get("/api/admin/roles")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3  # 至少3个预置角色


def test_create_role(auth_client):
    """测试创建角色"""
    response = auth_client.post(
        "/api/admin/roles",
        json={
            "name": "测试角色",
            "code": "test_role",
            "description": "测试用角色",
            "permissions": ["users:list"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "test_role"


def test_create_role_duplicate(auth_client):
    """测试重复编码"""
    response = auth_client.post(
        "/api/admin/roles",
        json={"name": "角色2", "code": "test_role", "permissions": []},
    )
    assert response.status_code == 400


def test_delete_system_role(auth_client):
    """测试删除系统角色"""
    # 获取superadmin角色ID
    response = auth_client.get("/api/admin/roles")
    roles = response.json()["items"]
    superadmin_id = next(r["id"] for r in roles if r["code"] == "superadmin")

    response = auth_client.delete(f"/api/admin/roles/{superadmin_id}")
    assert response.status_code == 400


def test_list_permissions(auth_client):
    """测试获取权限列表"""
    response = auth_client.get("/api/admin/roles/permissions")
    assert response.status_code == 200
    assert "permissions" in response.json()
