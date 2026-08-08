"""管理员认证测试fixture"""

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.main import app
from app.models.admin import Admin
from app.models.role import Role


@pytest.fixture(scope="module")
def test_engine():
    """每个测试模块使用独立的 SQLite 临时文件数据库"""
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
    """提供测试数据库会话"""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_roles(test_db):
    """创建测试角色"""
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
    """创建测试管理员"""
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
def client(test_db):
    """注入测试数据库的 TestClient"""

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(client, test_admin):
    """获取管理员token"""
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "testadmin", "password": "testpass123"},
    )
    return response.json()["data"]["access_token"]


@pytest.fixture(scope="module")
def auth_client(client, admin_token):
    """带鉴权的测试客户端"""
    client.headers["Authorization"] = f"Bearer {admin_token}"
    return client
