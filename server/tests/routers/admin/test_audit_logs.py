"""审计日志后端测试"""

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.backup_meta import MetaBase, get_backup_meta_db
from app.core.database import Base, get_db
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.main import app
from app.models.admin import Admin
from app.models.role import Role


@pytest.fixture(scope="module")
def test_engine():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_admin_")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    os.unlink(path)


@pytest.fixture(scope="module")
def test_db(test_engine):
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_meta_db():
    fd, path = tempfile.mkstemp(suffix="_meta.db", prefix="test_backup_meta_")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    from app.models.backup_record import BackupRecord  # noqa: F401

    MetaBase.metadata.create_all(bind=engine)
    MetaSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = MetaSession()
    yield db
    db.close()
    MetaBase.metadata.drop_all(bind=engine)
    engine.dispose()
    os.unlink(path)


@pytest.fixture(scope="module")
def test_roles(test_db):
    roles = {}
    for role_data in DEFAULT_ROLES:
        role = Role(
            name=role_data["name"],
            code=role_data["code"],
            description=role_data["description"],
            permissions=json.dumps(role_data["permissions"], ensure_ascii=False),
            is_system=role_data["is_system"],
        )
        test_db.add(role)
        test_db.commit()
        test_db.refresh(role)
        roles[role_data["code"]] = role
    return roles


@pytest.fixture(scope="module")
def test_admin(test_db, test_roles):
    admin = Admin(
        username="testadmin",
        password_hash=hash_password("testpass123"),
        nickname="测试管理员",
        role_id=test_roles["superadmin"].id,
        is_active=True,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture(scope="module")
def client(test_db, test_meta_db):
    def override_get_db():
        yield test_db

    def override_get_backup_meta_db():
        yield test_meta_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_backup_meta_db] = override_get_backup_meta_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(client, test_admin):
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    return response.json()["data"]["access_token"]


@pytest.fixture(scope="module")
def auth_client(client, admin_token):
    client.headers["X-Auth-Token"] = admin_token
    return client


# ==================== 测试用例 ====================


class TestAuditLogRecording:
    """测试审计日志自动记录"""

    def test_create_admin_generates_audit_log(self, auth_client):
        """POST 创建管理员应返回成功"""
        response = auth_client.post(
            "/api/admin/admins",
            json={
                "username": "audituser1",
                "password": "auditpass123",
                "nickname": "审计测试用户",
                "role_id": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_admin_generates_audit_log(self, auth_client, test_db):
        """DELETE 管理员应返回成功"""
        admin = Admin(
            username="to_delete",
            password_hash=hash_password("x"),
            nickname="待删除",
            role_id=2,
            is_active=True,
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

        response = auth_client.delete(f"/api/admin/admins/{admin.id}")
        assert response.status_code == 200

    def test_toggle_status_generates_audit_log(self, auth_client, test_db):
        """PUT 切换状态应返回成功"""
        admin = Admin(
            username="toggletest",
            password_hash=hash_password("x"),
            nickname="切换测试",
            role_id=2,
            is_active=True,
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

        response = auth_client.put(f"/api/admin/admins/{admin.id}/status")
        assert response.status_code == 200

    def test_reset_password_generates_audit_log(self, auth_client, test_db):
        """PUT 重置密码应返回成功"""
        admin = Admin(
            username="resetpwtest",
            password_hash=hash_password("oldpw"),
            nickname="重置密码测试",
            role_id=2,
            is_active=True,
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

        response = auth_client.put(
            f"/api/admin/admins/{admin.id}/password",
            json={"new_password": "newpass123"},
        )
        assert response.status_code == 200

    def test_create_role_generates_audit_log(self, auth_client):
        """POST 创建角色应返回成功"""
        response = auth_client.post(
            "/api/admin/roles",
            json={"name": "审计角色", "code": "audit_role", "description": "测试"},
        )
        assert response.status_code == 200

    def test_delete_role_generates_audit_log(self, auth_client, test_db):
        """DELETE 角色应返回成功"""
        role = Role(name="删除角色", code="del_role", description="测试", permissions="[]")
        test_db.add(role)
        test_db.commit()
        test_db.refresh(role)

        response = auth_client.delete(f"/api/admin/roles/{role.id}")
        assert response.status_code == 200


class TestAuditLogQuery:
    """测试审计日志查询接口"""

    def test_list_audit_logs(self, auth_client):
        """查询审计日志列表"""
        response = auth_client.get("/api/admin/audit-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]

    def test_filter_by_action(self, auth_client):
        """按 action 筛选"""
        response = auth_client.get("/api/admin/audit-logs", params={"action": "CREATE"})
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]["items"]:
            assert item["action"] == "CREATE"

    def test_filter_by_resource_type(self, auth_client):
        """按 resource_type 筛选"""
        response = auth_client.get("/api/admin/audit-logs", params={"resource_type": "admin"})
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]["items"]:
            assert item["resource_type"] == "admin"

    def test_filter_by_source(self, auth_client):
        """按 source 筛选"""
        response = auth_client.get("/api/admin/audit-logs", params={"source": "admin"})
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]["items"]:
            assert item["source"] == "admin"

    def test_pagination(self, auth_client):
        """分页参数"""
        response = auth_client.get("/api/admin/audit-logs", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) <= 2
        assert data["data"]["limit"] == 2
        assert data["data"]["offset"] == 0

    def test_response_fields(self, auth_client):
        """验证响应字段完整性"""
        response = auth_client.get("/api/admin/audit-logs", params={"limit": 1})
        assert response.status_code == 200
        data = response.json()
        if data["data"]["items"]:
            item = data["data"]["items"][0]
            required_fields = [
                "id",
                "source",
                "action",
                "resource_type",
                "request_path",
                "request_method",
                "response_code",
                "response_success",
                "response_message",
                "duration_ms",
                "ip_address",
                "user_agent",
                "created_at",
            ]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"

    def test_empty_result_when_no_match(self, auth_client):
        """无匹配结果时返回空列表"""
        response = auth_client.get(
            "/api/admin/audit-logs",
            params={"action": "NONEXISTENT_ACTION"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["items"] == []
        assert data["data"]["total"] == 0
