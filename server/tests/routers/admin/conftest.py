"""管理员认证测试fixture"""

import json
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.backup_meta import MetaBase, get_backup_meta_db
from app.core.database import Base, get_db
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.main import app
from app.models.admin import Admin
from app.models.role import Role

_MISSING = object()


def set_override(key, value):
    """精准注册一项 dependency override，返回还原回调（Step 132）。

    不用 `clear() + update(saved)`：module 级与 function 级 fixture 混用时，
    全量替换会互相抹掉对方的 override，导致请求打到错误的数据库。
    """
    previous = app.dependency_overrides.get(key, _MISSING)
    app.dependency_overrides[key] = value

    def restore():
        if previous is _MISSING:
            app.dependency_overrides.pop(key, None)
        else:
            app.dependency_overrides[key] = previous

    return restore


@pytest.fixture(autouse=True)
def _rollback_between_tests(test_db):
    """每个用例前后回滚 module 级会话，杜绝 PendingRollbackError 级联（Step 132）。

    module 级 test_db 被同模块多个用例共享，前一用例 flush 失败后会话进入
    rollback-only 状态，后续用例会全部报 PendingRollbackError。此处在每个用例
    开始前先 rollback，保证会话干净；仅回滚未提交事务，已 commit 的数据不受影响。
    """
    test_db.rollback()
    yield
    test_db.rollback()


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
def test_meta_db():
    """独立备份元数据库会话（临时文件隔离，不污染真实 backup_meta.db）"""
    fd, path = tempfile.mkstemp(suffix="_meta.db", prefix="test_backup_meta_")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    # 确保 BackupRecord 已注册到 MetaBase.metadata，create_all 才能建表
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
def client(test_db, test_meta_db, _app_client):
    """注入测试数据库的 TestClient（复用 session 级 _app_client，避免重复打开 TestClient 上下文）"""

    def override_get_db():
        yield test_db

    def override_get_backup_meta_db():
        yield test_meta_db

    restore_db = set_override(get_db, override_get_db)
    restore_meta = set_override(get_backup_meta_db, override_get_backup_meta_db)
    yield _app_client
    restore_db()
    restore_meta()


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
    """带鉴权的测试客户端

    TestClient 是 session 级共享对象，必须在 teardown 移除默认鉴权头，
    否则会污染后续模块的无鉴权用例（Step 132：media query token 401）。
    """
    client.headers["X-Auth-Token"] = admin_token
    yield client
    client.headers.pop("X-Auth-Token", None)
