import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app

# ==================== 测试数据库初始化（session 级） ====================


@pytest.fixture(scope="session", autouse=True)
def _init_test_database():
    """确保测试环境数据库（settings.DATABASE_URL）表已创建。

    pytest-env 注入 APP_ENV=test 后，config.py 加载 .env.test，
    DATABASE_URL 指向 ./data_test/tennis_diary_test.db。应用 lifespan 会用
    SessionLocal 对该库执行 init_default_roles，若表不存在会报 "no such table"。
    此 fixture 在首个测试前建表，保证 lifespan 可正常执行，且数据落在 data_test/。
    """
    import app.models  # noqa: F401  # 确保所有模型注册到 Base.metadata
    from app.core.database import engine

    Base.metadata.create_all(bind=engine)
    return engine


# ==================== 目录隔离（autouse，全局生效） ====================


@pytest.fixture(autouse=True)
def _isolate_data_dirs(tmp_path, monkeypatch):
    """将 DATA_DIR / UPLOAD_DIR / LOG_DIR 隔离到临时目录，杜绝污染真实 data_test/。

    仅隔离 settings 的属性值，不会重建全局 engine（engine 由 dependency
    override 注入 test_db 使用，业务路由读的是 settings.UPLOAD_DIR/DATA_DIR）。
    """
    from app.core.config import settings

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
    monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))
    return data_dir


@pytest.fixture
def data_dir(_isolate_data_dirs):
    """提供已隔离的临时 DATA_DIR，供需要构造文件结构的测试使用"""
    return _isolate_data_dirs


# ==================== 测试数据库 ====================


@pytest.fixture(scope="function")
def test_engine():
    """每个测试函数使用独立的 SQLite 临时文件数据库

    注意：不能使用 :memory:，因为 FastAPI async handler 在 TestClient 的
    asyncio portal 中运行时可能使用不同线程，而 :memory: 数据库在不同连接间
    是独立的，会导致 "no such table" 错误。
    """
    import os
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    os.unlink(path)


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
