"""文件使用标记测试（Step 111）

覆盖 classify_file_usage 四类状态 + Admin 端点响应包含 usage_status：
- marked_deleted：deleted_at 非空
- unreferenced / ref_count <= 0 / 业务记录不再引用
- in_use：业务记录仍引用该 rel_path
- orphan：扫描结果补 usage_status

路径匹配按精确字符串比对：
- user：User.avatar_url == rel_path
- gear：Gear.photo == rel_path
- analysis：video_url / thumb / highlights / pose 任一包含 rel_path
"""

import hashlib
import json
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


def _insert_file(db, user_id=None, rel_path=None, md5=None, **overrides):
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
def auth_client(test_engine, test_db):
    """带 mock 用户和 admin token 的 TestClient"""
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
    headers = {"X-Auth-Token": token}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_media] = override_get_current_user_media
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    client = TestClient(app, headers=headers)
    yield client
    app.dependency_overrides.clear()


# ==================== classify_file_usage 单元测试 ====================


class TestClassifyFileUsage:
    """纯函数 classify_file_usage 的行为测试，绕过路由层直接验证核心逻辑。"""

    def test_marked_deleted(self, test_engine, test_db):
        rec = _insert_file(test_db, rel_path="mk/1/a.jpg", deleted_at=time.time())
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "marked_deleted"
        assert "待物理清理" in reason

    def test_ref_count_zero(self, test_engine, test_db):
        rec = _insert_file(test_db, ref_count=0)
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "归零" in reason

    def test_no_business_id(self, test_engine, test_db):
        rec = _insert_file(test_db, business_id=None, business_type=None)
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "未绑定业务记录" in reason

    def test_user_source_infer_in_use(self, test_engine, test_db):
        uid = 1100
        rel = f"avatars/{uid}/pic.jpg"
        test_db.add(User(id=uid, openid=f"oid_{uid}", avatar_url=rel))
        test_db.commit()
        # business_type=None, upload_source="avatar" → 走 upload_source 推断
        rec = _insert_file(
            test_db,
            user_id=uid,
            rel_path=rel,
            business_type=None,
            upload_source="avatar",
            business_id=None,
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "头像引用有效" in reason

    def test_user_source_infer_unreferenced(self, test_engine, test_db):
        uid = 1101
        rel = f"avatars/{uid}/pic.jpg"
        # 没有对应的 User 记录
        rec = _insert_file(
            test_db,
            user_id=uid,
            rel_path=rel,
            business_type=None,
            upload_source="avatar",
            business_id=None,
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "头像引用已失效" in reason

    def test_gear_source_infer_in_use(self, test_engine, test_db):
        uid = 2100
        rel = f"gears/{uid}/ball.jpg"
        test_db.add(Gear(id=300, user_id=uid, photo=rel))
        test_db.commit()
        rec = _insert_file(
            test_db,
            user_id=uid,
            rel_path=rel,
            business_type=None,
            upload_source="gear_image",
            business_id=None,
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "装备图片引用有效" in reason

    def test_video_source_infer_in_use(self, test_engine, test_db):
        uid = 3100
        aid = 700
        rel = f"videos/{uid}/{aid}.mp4"
        test_db.add(Analysis(id=aid, user_id=uid, date="2026-01-01", video_url=rel))
        test_db.commit()
        rec = _insert_file(
            test_db,
            user_id=uid,
            rel_path=rel,
            business_type=None,
            upload_source="video",
            business_id=None,
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "分析报告引用有效" in reason

    def test_unknown_source_no_business_id(self, test_engine, test_db):
        uid = 4100
        rel = f"unknown/{uid}/x.jpg"
        rec = _insert_file(
            test_db,
            user_id=uid,
            rel_path=rel,
            business_type=None,
            upload_source="other",
            business_id=None,
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "未绑定业务记录" in reason

    def test_user_in_use(self, test_engine, test_db):
        uid = 1000
        rel = f"avatars/{uid}/pic.jpg"
        test_db.add(User(id=uid, openid=f"oid_{uid}", avatar_url=rel))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="user", business_id=uid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "头像引用有效" in reason

    def test_user_unreferenced_missing_record(self, test_engine, test_db):
        uid = 1001
        rel = f"avatars/{uid}/pic.jpg"
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="user", business_id=uid + 999
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "头像引用已失效" in reason

    def test_user_unreferenced_path_mismatch(self, test_engine, test_db):
        uid = 1002
        rel = f"avatars/{uid}/pic.jpg"
        test_db.add(User(id=uid, openid=f"oid_{uid}", avatar_url="avatars/1002/other.jpg"))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="user", business_id=uid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "头像引用已失效" in reason

    def test_gear_in_use(self, test_engine, test_db):
        uid = 2000
        gid = 500
        rel = f"gears/{uid}/{gid}.jpg"
        test_db.add(Gear(id=gid, user_id=uid, photo=rel))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="gear", business_id=gid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "装备图片引用有效" in reason

    def test_gear_unreferenced_missing_record(self, test_engine, test_db):
        uid = 2001
        gid = 501
        rel = f"gears/{uid}/{gid}.jpg"
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="gear", business_id=gid + 777
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "装备记录引用已失效" in reason

    def test_gear_unreferenced_path_mismatch(self, test_engine, test_db):
        uid = 2002
        gid = 502
        rel = f"gears/{uid}/{gid}.jpg"
        test_db.add(Gear(id=gid, user_id=uid, photo="data:image/png;base64,abc"))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="gear", business_id=gid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "装备记录引用已失效" in reason

    def test_analysis_in_use_video_url(self, test_engine, test_db):
        uid = 3000
        aid = 600
        rel = f"videos/{uid}/{aid}.mp4"
        test_db.add(Analysis(id=aid, user_id=uid, date="2026-01-01", video_url=rel))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="analysis", business_id=aid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "分析报告引用有效" in reason

    def test_analysis_in_use_thumb(self, test_engine, test_db):
        uid = 3001
        aid = 601
        rel = f"analyses/{uid}/{aid}_thumb.jpg"
        test_db.add(Analysis(id=aid, user_id=uid, date="2026-01-01", thumb=rel))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="analysis", business_id=aid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "分析报告引用有效" in reason

    def test_analysis_in_use_highlights(self, test_engine, test_db):
        uid = 3002
        aid = 602
        rel = f"frames/{uid}/{aid}_f1.jpg"
        test_db.add(Analysis(id=aid, user_id=uid, date="2026-01-01", highlights=json.dumps([rel])))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="analysis", business_id=aid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "分析报告引用有效" in reason

    def test_analysis_in_use_pose_skeleton(self, test_engine, test_db):
        uid = 3003
        aid = 603
        rel = f"skeleton/{uid}/{aid}_sk.mp4"
        pose = {"skeleton_video_url": rel}
        test_db.add(Analysis(id=aid, user_id=uid, date="2026-01-01", pose=json.dumps(pose)))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="analysis", business_id=aid
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "in_use"
        assert "分析报告引用有效" in reason

    def test_analysis_unreferenced_missing_record(self, test_engine, test_db):
        uid = 3004
        aid = 604
        rel = f"videos/{uid}/{aid}.mp4"
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="analysis", business_id=aid + 10
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "分析报告引用已失效" in reason

    def test_unknown_business_type(self, test_engine, test_db):
        uid = 4000
        rel = f"other/{uid}/x.jpg"
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="diary", business_id=123
        )
        status, reason = file_service.classify_file_usage(test_db, rec)
        assert status == "unreferenced"
        assert "未知业务类型 diary" in reason


# ==================== 扫描孤儿补 usage_status ====================


class TestScanOrphanUsageStatus:
    def test_orphan_has_usage_status(self, test_engine, test_db, tmp_path, monkeypatch):
        from app.core.config import settings

        data_dir = tmp_path / "data"
        upload_dir = data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
        monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))

        # 放一个孤儿文件到磁盘
        orphan_rel = "orphan-test/leaked.jpg"
        orphan_abs = upload_dir / orphan_rel
        orphan_abs.parent.mkdir(parents=True, exist_ok=True)
        orphan_abs.write_bytes(b"leaked content")

        result = file_service.scan_orphan_files(test_db)
        orphans = result["orphans"]
        assert len(orphans) >= 1
        matched = [o for o in orphans if o["rel_path"] == orphan_rel]
        assert len(matched) == 1
        assert matched[0]["usage_status"] == "orphan"
        assert "磁盘孤儿" in matched[0]["usage_reason"]


# ==================== Admin 端点集成测试 ====================


class TestAdminFileUsageListEndpoint:
    def test_list_response_contains_usage_status(self, auth_client, test_db, tmp_path, monkeypatch):
        from app.core.config import settings

        data_dir = tmp_path / "data"
        upload_dir = data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
        monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))

        uid = 1
        rel = "usage-list/1/a.jpg"
        test_db.add(User(id=uid, openid="u1", avatar_url=rel))
        test_db.commit()
        rec = _insert_file(
            test_db, user_id=uid, rel_path=rel, business_type="user", business_id=uid
        )

        resp = auth_client.get("/api/admin/files")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        found = [i for i in items if i["id"] == rec.id]
        assert len(found) == 1
        assert found[0]["usage_status"] == "in_use"
        assert found[0]["usage_reason"] == "用户头像引用有效"

    def test_list_marked_deleted_filtered(self, auth_client, test_db):
        rel = "usage-del/2/b.jpg"
        rec = _insert_file(test_db, user_id=2, rel_path=rel, deleted_at=time.time())
        resp = auth_client.get("/api/admin/files")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        # 软删文件默认被过滤，不返回
        assert not any(i["id"] == rec.id for i in items)

    def test_stats_include_new_counts(self, auth_client, test_db):
        # 构造一条软删
        _insert_file(test_db, deleted_at=time.time())
        # 构造一条 ref_count=0
        _insert_file(test_db, ref_count=0)
        resp = auth_client.get("/api/admin/files/stats/summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data.get("marked_deleted_count") == 1
        assert data.get("unreferenced_count") == 1
