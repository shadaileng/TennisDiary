import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.auth import get_current_user
from app.main import app


# ==================== 测试数据库 ====================

@pytest.fixture(scope="function")
def test_engine():
    """每个测试函数使用独立的 SQLite 内存数据库"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """提供测试数据库会话"""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# ==================== 测试用户 ====================

@pytest.fixture(scope="function")
def mock_user():
    """模拟已登录用户"""
    from app.models.user import User

    class MockUser:
        id = 1
        openid = "test_openid_abc123"
        nickname = "测试用户"
        avatar_url = ""

    return MockUser()


# ==================== FastAPI TestClient ====================

@pytest.fixture(scope="function")
def client(test_db):
    """注入测试数据库和 mock 鉴权的 TestClient"""

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client, mock_user, test_db):
    """带 mock 鉴权的 TestClient，所有请求自动通过 get_current_user"""

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()
