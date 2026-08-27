"""Admin 立即清理孤儿文件测试（Step 112）

覆盖：
- POST /api/admin/files/cleanup-orphans 物理删除选中孤儿文件
- 删除后文件不再出现在扫描结果中
- 空列表请求不报错
"""

import os
import tempfile
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import get_current_admin, get_current_user, get_current_user_media
from app.core.database import Base, get_db
from app.main import app

_seq = 0


def _next_seq():
    global _seq
    _seq += 1
    return _seq


def _write_file(rel_path: str, content: bytes = b"orphan-content") -> str:
    abs_path = os.path.join(os.path.abspath(app.state.data_dir or ""), rel_path)
    # fallback to settings
    from app.core.config import settings

    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
    return rel_path


@pytest.fixture(scope="function")
def admin_client(test_engine):
    from jose import jwt as _jwt

    from app.core.auth import ADMIN_JWT_ALGORITHM, ADMIN_JWT_SECRET

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()

    def override_get_db():
        yield db

    def override_get_current_user():
        class U:
            id = 999
            openid = "test_openid"
            nickname = "tester"
            avatar_url = ""

        return U()

    def override_get_current_user_media():
        return override_get_current_user()

    def override_get_current_admin():
        class A:
            id = 1
            username = "admin"
            is_active = True
            role_id = 1

        return A()

    token = _jwt.encode(
        {"sub": "admin:1", "type": "admin", "exp": time.time() + 86400},
        ADMIN_JWT_SECRET,
        algorithm=ADMIN_JWT_ALGORITHM,
    )
    headers = {"X-Auth-Token": token}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_media] = override_get_current_user_media
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    client = TestClient(app, headers=headers)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_engine():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_cleanup_")
    os.close(fd)
    eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()
    os.unlink(path)


class TestCleanupOrphans:
    def test_cleanup_orphan_files(self, admin_client, tmp_path, monkeypatch):
        from app.core.config import settings

        data_dir = tmp_path / "data"
        upload_dir = data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
        monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))

        client = admin_client

        # 创建两个孤儿文件
        rel1 = "orphan-cleanup/a.jpg"
        rel2 = "orphan-cleanup/b.jpg"
        abs1 = os.path.join(upload_dir, rel1)
        abs2 = os.path.join(upload_dir, rel2)
        os.makedirs(os.path.dirname(abs1), exist_ok=True)
        os.makedirs(os.path.dirname(abs2), exist_ok=True)
        with open(abs1, "wb") as f:
            f.write(b"orphan-a")
        with open(abs2, "wb") as f:
            f.write(b"orphan-b")

        # 先扫描确认两个孤儿
        scan_resp = client.post("/api/admin/files/scan")
        assert scan_resp.status_code == 200
        orphans = scan_resp.json()["data"]["orphans"]
        orphan_paths = [o["rel_path"] for o in orphans]
        assert rel1 in orphan_paths
        assert rel2 in orphan_paths

        # 清理选中两个
        resp = client.post(
            "/api/admin/files/cleanup-orphans",
            json={"files": [rel1, rel2]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["cleaned"] == 2

        # 再次扫描，确认已消失
        scan_resp2 = client.post("/api/admin/files/scan")
        assert scan_resp2.status_code == 200
        orphans2 = scan_resp2.json()["data"]["orphans"]
        orphan_paths2 = [o["rel_path"] for o in orphans2]
        assert rel1 not in orphan_paths2
        assert rel2 not in orphan_paths2

        # 确认磁盘文件已删除
        assert not os.path.exists(abs1)
        assert not os.path.exists(abs2)

    def test_cleanup_empty_list(self, admin_client, tmp_path, monkeypatch):
        from app.core.config import settings

        data_dir = tmp_path / "data"
        upload_dir = data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
        monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))

        client = admin_client

        resp = client.post("/api/admin/files/cleanup-orphans", json={"files": []})
        assert resp.status_code == 200
        assert resp.json()["data"]["cleaned"] == 0

    def test_cleanup_skips_nonexistent(self, admin_client, tmp_path, monkeypatch):
        from app.core.config import settings

        data_dir = tmp_path / "data"
        upload_dir = data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
        monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))

        client = admin_client

        # 清理一个不存在的文件，应返回 cleaned=0 不报错
        resp = client.post(
            "/api/admin/files/cleanup-orphans",
            json={"files": ["nonexistent/path.jpg"]},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["cleaned"] == 0
