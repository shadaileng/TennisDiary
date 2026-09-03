"""Admin 批量删除文件测试（多选删除可清除文件）

覆盖：
- POST /api/admin/files/batch-delete 批量软删多条记录
- 含不存在 ID 时跳过不报错
- 空列表请求返回 400
- 引用归零时物理删除磁盘文件
"""

import hashlib
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
from app.models.file import File

_seq = 0


def _next_seq():
    global _seq
    _seq += 1
    return _seq


def _insert_file(db, user_id=None, rel_path=None, md5=None, **overrides):
    seq = _next_seq()
    if user_id is None:
        user_id = 10000 + seq
    if rel_path is None:
        rel_path = f"batch-test/{user_id}/file-{seq}.jpg"
    if md5 is None:
        md5 = hashlib.md5(f"batch-content-{seq}".encode()).hexdigest()
    defaults = dict(
        user_id=user_id,
        md5=md5,
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=42,
        mime_type="image/jpeg",
        upload_source="other",
        ref_count=1,
        created_at=time.time(),
    )
    defaults.update(overrides)
    rec = File(**defaults)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@pytest.fixture(scope="function")
def test_engine():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_batch_")
    os.close(fd)
    eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()
    os.unlink(path)


@pytest.fixture(scope="function")
def test_db(test_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def auth_client(test_engine, test_db, tmp_path, monkeypatch):
    from jose import jwt as _jwt

    from app.core.auth import ADMIN_JWT_ALGORITHM, ADMIN_JWT_SECRET
    from app.core.config import settings

    data_dir = tmp_path / "data"
    upload_dir = data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))

    def override_get_db():
        yield test_db

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


class TestBatchDelete:
    def test_batch_delete_multiple(self, auth_client, test_db):
        f1 = _insert_file(test_db, upload_source="other", business_type=None, business_id=None)
        f2 = _insert_file(test_db, upload_source="other", business_type=None, business_id=None)
        f3 = _insert_file(test_db, upload_source="other", business_type=None, business_id=None)

        resp = auth_client.post(
            "/api/admin/files/batch-delete",
            json={"file_ids": [f1.id, f2.id, f3.id]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["deleted"] == 3
        assert data["skipped"] == 0
        # 测试文件未在磁盘创建，物理清理计数为 0（逻辑已软删）
        assert data["disk_removed"] == 0

        for fid in (f1.id, f2.id, f3.id):
            rec = test_db.query(File).filter(File.id == fid).first()
            assert rec.deleted_at is not None
            assert rec.ref_count == 0

    def test_batch_delete_skips_nonexistent(self, auth_client, test_db):
        f1 = _insert_file(test_db, upload_source="other", business_type=None, business_id=None)
        resp = auth_client.post(
            "/api/admin/files/batch-delete",
            json={"file_ids": [f1.id, 999999]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["deleted"] == 1
        assert data["skipped"] == 1
        assert any("999999" in e for e in data["errors"])

    def test_batch_delete_empty(self, auth_client):
        resp = auth_client.post("/api/admin/files/batch-delete", json={"file_ids": []})
        assert resp.status_code == 400

    def test_batch_delete_physical_cleanup(self, auth_client, test_db, tmp_path, monkeypatch):
        from app.core.config import settings

        rel = "batch-physical/del.jpg"
        abs_path = os.path.join(settings.UPLOAD_DIR, rel)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(b"to-be-removed")

        rec = _insert_file(test_db, rel_path=rel, ref_count=1)
        assert os.path.exists(abs_path)

        resp = auth_client.post(
            "/api/admin/files/batch-delete",
            json={"file_ids": [rec.id]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["deleted"] == 1
        assert data["disk_removed"] == 1
        assert not os.path.exists(abs_path)
