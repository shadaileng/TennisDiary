"""文件使用状态测试（Step 111 / 138：基于业务引用注册表）

覆盖 `file_service.classify` 的状态判定 + Admin 端点响应包含 usage_status：
- marked_deleted：deleted_at 非空
- missing：已登记但物理文件缺失
- in_use：业务表（user/gear/analysis）仍引用该 rel_path
- unreferenced：无任何业务引用
- orphan / unregistered_ref：scan() 对未登记路径的分类

判定口径统一来自 `file_refs` 注册表，不再使用「某类来源不被消费」的硬编码名单。
"""

import hashlib
import json
import os
import tempfile
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import get_current_admin, get_current_user, get_current_user_media
from app.core.database import Base, get_db
from app.main import app
from app.models.analysis import Analysis
from app.models.file import File
from app.models.gear import Gear
from app.models.user import User
from app.services import file_service

_seq = 0


def _next_seq():
    global _seq
    _seq += 1
    return _seq


def _insert_file(db, user_id=None, rel_path=None, md5=None, write_disk=True, **overrides):
    """插入一条文件记录；默认同时在受管目录创建物理文件"""
    seq = _next_seq()
    if user_id is None:
        user_id = 10000 + seq
    if rel_path is None:
        rel_path = f"usage-test/{user_id}/file-{seq}.jpg"
    if md5 is None:
        md5 = hashlib.md5(f"test-content-{seq}".encode()).hexdigest()
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
    if write_disk and not rec.deleted_at:
        file_service.write_bytes(file_service.abs_of(rel_path), b"content")
    return rec


@pytest.fixture(scope="function")
def test_engine():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_usage_")
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
def auth_client(test_engine, test_db, _app_client):
    """带 mock 用户和 admin token 的 TestClient（复用 session 级 _app_client）"""
    from jose import jwt as _jwt

    from app.core.auth import ADMIN_JWT_ALGORITHM, ADMIN_JWT_SECRET

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

    saved_overrides = dict(app.dependency_overrides)
    saved_headers = dict(_app_client.headers)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_media] = override_get_current_user_media
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    _app_client.headers["X-Auth-Token"] = token
    yield _app_client
    _app_client.headers.clear()
    _app_client.headers.update(saved_headers)
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved_overrides)


# ==================== classify 单元测试 ====================


def _classify(db, rec):
    return file_service.classify(db, [rec])[rec.id]


class TestClassify:
    """基于业务引用注册表的状态判定"""

    def test_marked_deleted(self, test_db):
        rec = _insert_file(test_db, rel_path="mk/1/a.jpg", deleted_at=time.time())
        status, reason = _classify(test_db, rec)
        assert status == "marked_deleted"
        assert "标记删除" in reason

    def test_missing_physical_file(self, test_db):
        rec = _insert_file(test_db, rel_path="ms/1/a.jpg", write_disk=False)
        status, reason = _classify(test_db, rec)
        assert status == "missing"
        assert "物理文件缺失" in reason

    def test_user_avatar_in_use(self, test_db):
        rel = "avatars/11/a.jpg"
        test_db.add(User(id=11, openid="u11", avatar_url=rel))
        test_db.commit()
        rec = _insert_file(test_db, user_id=11, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_user_avatar_unreferenced_on_mismatch(self, test_db):
        test_db.add(User(id=12, openid="u12", avatar_url="avatars/12/other.jpg"))
        test_db.commit()
        rec = _insert_file(test_db, user_id=12, rel_path="avatars/12/a.jpg")
        assert _classify(test_db, rec)[0] == "unreferenced"

    def test_gear_photo_in_use(self, test_db):
        rel = "gears/13/a.jpg"
        test_db.add(Gear(user_id=13, name="拍", photo=rel))
        test_db.commit()
        rec = _insert_file(test_db, user_id=13, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_analysis_video_url_in_use(self, test_db):
        rel = "videos/14/a.mp4"
        test_db.add(Analysis(user_id=14, date="2026-01-01", video_url=rel))
        test_db.commit()
        rec = _insert_file(test_db, user_id=14, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_analysis_thumb_in_use(self, test_db):
        rel = "videos/15/thumb.jpg"
        test_db.add(Analysis(user_id=15, date="2026-01-01", thumb=rel))
        test_db.commit()
        rec = _insert_file(test_db, user_id=15, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_analysis_highlights_json_list_in_use(self, test_db):
        rel = "videos/16/h.jpg"
        test_db.add(Analysis(user_id=16, date="2026-01-01", highlights=json.dumps([rel])))
        test_db.commit()
        rec = _insert_file(test_db, user_id=16, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_analysis_pose_skeleton_video_in_use(self, test_db):
        rel = "videos/17/sk.mp4"
        test_db.add(
            Analysis(
                user_id=17,
                date="2026-01-01",
                pose=json.dumps({"skeleton_video_url": rel, "skeleton_frames": []}),
            )
        )
        test_db.commit()
        rec = _insert_file(test_db, user_id=17, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_analysis_pose_frames_list_in_use(self, test_db):
        rel = "videos/18/sk0.jpg"
        test_db.add(
            Analysis(user_id=18, date="2026-01-01", pose=json.dumps({"skeleton_frames": [rel]}))
        )
        test_db.commit()
        rec = _insert_file(test_db, user_id=18, rel_path=rel)
        assert _classify(test_db, rec)[0] == "in_use"

    def test_binding_alone_marks_in_use(self, test_db):
        """仅存在绑定关系（无业务表字段）也判定为在用"""
        rec = _insert_file(test_db, user_id=19, rel_path="videos/19/bound.mp4")
        file_service.bind(test_db, 19, rec.rel_path, "analysis", 1, "video_url")
        test_db.commit()
        assert _classify(test_db, rec)[0] == "in_use"

    def test_unreferenced_when_no_business(self, test_db):
        rec = _insert_file(test_db, user_id=20, rel_path="videos/20/free.mp4")
        assert _classify(test_db, rec)[0] == "unreferenced"


# ==================== scan 五态 ====================


class TestScanStatus:
    def test_orphan_status(self, test_db):
        file_service.write_bytes(file_service.abs_of("orphan-test/leaked.jpg"), b"leaked")
        result = file_service.scan(test_db)
        matched = [i for i in result["items"] if i["rel_path"] == "orphan-test/leaked.jpg"]
        assert len(matched) == 1
        assert matched[0]["status"] == "orphan"
        assert "磁盘孤儿" in matched[0]["reason"]

    def test_unregistered_ref_status(self, test_db):
        rel = "gears/21/not-registered.jpg"
        test_db.add(Gear(user_id=21, name="拍", photo=rel))
        test_db.commit()
        result = file_service.scan(test_db)
        matched = [i for i in result["items"] if i["rel_path"] == rel]
        assert len(matched) == 1
        assert matched[0]["status"] == "unregistered_ref"


# ==================== Admin 端点集成测试 ====================


class TestAdminFileUsageListEndpoint:
    def test_list_response_contains_usage_status(self, auth_client, test_db):
        uid = 1
        rel = "usage-list/1/a.jpg"
        test_db.add(User(id=uid, openid="u1", avatar_url=rel))
        test_db.commit()
        rec = _insert_file(test_db, user_id=uid, rel_path=rel)

        resp = auth_client.get("/api/admin/files")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        found = [i for i in items if i["id"] == rec.id]
        assert len(found) == 1
        assert found[0]["usage_status"] == "in_use"

    def test_list_marked_deleted_filtered(self, auth_client, test_db):
        rec = _insert_file(test_db, user_id=2, rel_path="usage-del/2/b.jpg", deleted_at=time.time())
        resp = auth_client.get("/api/admin/files")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert not any(i["id"] == rec.id for i in items)

    def test_list_filter_by_usage_status(self, auth_client, test_db):
        used = "usage-filter/3/used.jpg"
        free = "usage-filter/3/free.jpg"
        test_db.add(User(id=3, openid="u3", avatar_url=used))
        test_db.commit()
        _insert_file(test_db, user_id=3, rel_path=used)
        _insert_file(test_db, user_id=3, rel_path=free)

        resp = auth_client.get("/api/admin/files", params={"usage_status": "unreferenced"})
        assert resp.status_code == 200
        paths = {i["rel_path"] for i in resp.json()["data"]["items"]}
        assert free in paths
        assert used not in paths

    def test_stats_include_new_counts(self, auth_client, test_db):
        _insert_file(test_db, deleted_at=time.time())
        _insert_file(test_db, ref_count=0)
        resp = auth_client.get("/api/admin/files/stats/summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data.get("marked_deleted_count") == 1
        assert data.get("unreferenced_count") >= 1

    def test_scan_endpoint_returns_status_counts(self, auth_client, test_db):
        file_service.write_bytes(file_service.abs_of("scan-test/x.jpg"), b"x")
        resp = auth_client.post("/api/admin/files/scan")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "status_counts" in data
        assert data["orphan_files"] >= 1
