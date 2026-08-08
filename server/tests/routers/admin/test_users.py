"""用户管理测试"""


def test_list_users(auth_client, test_db):
    """测试用户列表"""
    response = auth_client.get("/api/admin/users")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "items" in data
    assert "total" in data


def test_get_user_detail(auth_client, test_db):
    """测试获取用户详情"""
    # 先创建一个测试用户
    from app.models.user import User

    user = User(openid="test_openid_123", nickname="测试用户")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    user_id = user.id

    response = auth_client.get(f"/api/admin/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["data"]["nickname"] == "测试用户"


def test_get_user_not_found(auth_client):
    """测试获取不存在的用户"""
    response = auth_client.get("/api/admin/users/99999")
    assert response.status_code == 404


def test_delete_user(auth_client, test_db):
    """测试删除用户"""
    from app.models.user import User

    user = User(openid="test_delete_openid", nickname="待删除用户")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    user_id = user.id

    response = auth_client.delete(f"/api/admin/users/{user_id}")
    assert response.status_code == 200

    # 验证已删除
    response = auth_client.get(f"/api/admin/users/{user_id}")
    assert response.status_code == 404
