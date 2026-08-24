"""Admin 文件管理路由测试（5.4 Admin 端点）

覆盖：
- GET  /api/admin/files          列表（分页 + 过滤）
- GET  /api/admin/files/{id}     详情（含 derived_files）
- DELETE /api/admin/files/{id}   软删除（引用归零 + 共享路径检查）
- POST /api/admin/files/cleanup  清理旧文件
- GET  /api/admin/files/stats    统计摘要
"""

import hashlib
import os
import time

from app.core.config import settings
from app.models.file import File

_seq = 0


def _next_seq():
    global _seq
    _seq += 1
    return _seq


def _next_uid():
    """每个测试用唯一 user_id，避免跨测试唯一约束冲突"""
    return 5000 + _next_seq()


def _write_file(rel_path: str, content: bytes = b"test-content") -> str:
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
    return rel_path


def _insert_file(test_db, user_id=None, rel_path=None, md5=None, **overrides) -> File:
    seq = _next_seq()
    if user_id is None:
        user_id = _next_uid()
    if rel_path is None:
        rel_path = f"admin-test/{user_id}/file-{seq}.jpg"
    if md5 is None:
        md5 = hashlib.md5(f"test-content-{seq}".encode()).hexdigest()
    defaults = dict(
        user_id=user_id,
        md5=md5,
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=12,
        mime_type="image/jpeg",
        upload_source="gear_image",
        ref_count=1,
        created_at=time.time(),
    )
    defaults.update(overrides)
    record = File(**defaults)
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


class TestAdminFileList:
    """GET /api/admin/files"""

    def test_list_files(self, auth_client, test_db):
        uid = _next_uid()
        _insert_file(test_db, user_id=uid, rel_path=f"list-a-{uid}.jpg")
        _insert_file(test_db, user_id=uid + 1, rel_path=f"list-b-{uid}.jpg")
        resp = auth_client.get("/api/admin/files")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    def test_list_filter_by_user(self, auth_client, test_db):
        uid = _next_uid()
        _insert_file(test_db, user_id=uid, rel_path=f"filter-u-{uid}.jpg")
        _insert_file(test_db, user_id=uid + 1, rel_path=f"filter-u-{uid + 1}.jpg")
        resp = auth_client.get(f"/api/admin/files?user_id={uid}")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(i["user_id"] == uid for i in items)

    def test_list_filter_by_source(self, auth_client, test_db):
        uid = _next_uid()
        _insert_file(test_db, user_id=uid, rel_path=f"src-a-{uid}.jpg", upload_source="avatar")
        _insert_file(test_db, user_id=uid, rel_path=f"src-b-{uid}.jpg", upload_source="video_frame")
        resp = auth_client.get("/api/admin/files?upload_source=avatar")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(i["upload_source"] == "avatar" for i in items)

    def test_list_pagination(self, auth_client, test_db):
        uid = _next_uid()
        for i in range(5):
            _insert_file(test_db, user_id=uid, rel_path=f"page-{uid}-{i}.jpg")
        resp = auth_client.get("/api/admin/files?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] >= 5


class TestAdminFileDetail:
    """GET /api/admin/files/{file_id}"""

    def test_detail_includes_derived(self, auth_client, test_db):
        uid = _next_uid()
        biz_id = uid
        main = _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"derived-main-{uid}.jpg",
            business_type="analysis",
            business_id=biz_id,
        )
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"derived-sub-{uid}.jpg",
            business_type="analysis",
            business_id=biz_id,
            upload_source="video_frame",
        )
        resp = auth_client.get(f"/api/admin/files/{main.id}")
        assert resp.status_code == 200
        detail = resp.json()["data"]
        assert len(detail["derived_files"]) == 1
        assert f"derived-sub-{uid}" in detail["derived_files"][0]["rel_path"]

    def test_detail_not_found(self, auth_client):
        resp = auth_client.get("/api/admin/files/999999")
        assert resp.status_code == 404


class TestAdminFileDelete:
    """DELETE /api/admin/files/{file_id}"""

    def test_delete_soft_marks_deleted(self, auth_client, test_db):
        uid = _next_uid()
        record = _insert_file(test_db, user_id=uid, rel_path=f"to-del-{uid}.jpg")
        resp = auth_client.delete(f"/api/admin/files/{record.id}")
        assert resp.status_code == 200
        test_db.refresh(record)
        assert record.deleted_at is not None

    def test_delete_removes_disk_when_no_sharing(self, auth_client, test_db):
        uid = _next_uid()
        rel = f"del-disk-{uid}.jpg"
        _write_file(rel)
        record = _insert_file(test_db, user_id=uid, rel_path=rel)
        abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel)
        assert os.path.isfile(abs_path)

        auth_client.delete(f"/api/admin/files/{record.id}")
        assert not os.path.isfile(abs_path)

    def test_delete_keeps_disk_when_shared(self, auth_client, test_db):
        """秒传共享路径时不删物理文件（不同用户同 MD5）"""
        uid1 = _next_uid()
        uid2 = _next_uid()
        rel = f"shared-keep-{uid1}.jpg"
        _write_file(rel)
        md5 = hashlib.md5(f"shared-{uid1}".encode()).hexdigest()
        r1 = _insert_file(test_db, user_id=uid1, rel_path=rel, md5=md5, upload_source="avatar")
        _insert_file(test_db, user_id=uid2, rel_path=rel, md5=md5, upload_source="gear_image")

        auth_client.delete(f"/api/admin/files/{r1.id}")
        abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel)
        assert os.path.isfile(abs_path)

    def test_delete_not_found(self, auth_client):
        resp = auth_client.delete("/api/admin/files/999999")
        assert resp.status_code == 404


class TestAdminFileCleanup:
    """POST /api/admin/files/cleanup"""

    def test_cleanup_removes_old_deleted(self, auth_client, test_db):
        uid = _next_uid()
        rel = f"cleanup-old-{uid}.jpg"
        _write_file(rel, b"cleanup-content")
        record = _insert_file(test_db, user_id=uid, rel_path=rel)
        record.deleted_at = time.time() - (31 * 86400)
        test_db.commit()

        resp = auth_client.post("/api/admin/files/cleanup?days=30")
        assert resp.status_code == 200
        # 物理文件被清理（或记录被删除，无论文件是否在磁盘上）
        test_db.expire_all()
        from app.models.file import File

        remaining = test_db.query(File).filter(File.id == record.id).first()
        assert remaining is None

    def test_cleanup_keeps_recent_deleted(self, auth_client, test_db):
        uid = _next_uid()
        record = _insert_file(test_db, user_id=uid, rel_path=f"cleanup-recent-{uid}.jpg")
        record.deleted_at = time.time() - (5 * 86400)
        test_db.commit()

        resp = auth_client.post("/api/admin/files/cleanup?days=30")
        assert resp.status_code == 200
        assert resp.json()["data"]["cleaned"] == 0


class TestAdminFileStats:
    """GET /api/admin/files/stats/summary"""

    def test_stats_returns_counts(self, auth_client, test_db):
        uid = _next_uid()
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"stats-a-{uid}.jpg",
            upload_source="avatar",
            size_bytes=100,
        )
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"stats-b-{uid}.jpg",
            upload_source="gear_image",
            size_bytes=200,
        )
        resp = auth_client.get("/api/admin/files/stats/summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_count"] >= 2
        assert data["total_size_bytes"] >= 300
        assert "by_source" in data

    def test_stats_by_source(self, auth_client, test_db):
        uid = _next_uid()
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"src-av-{uid}.jpg",
            upload_source="avatar",
            size_bytes=50,
        )
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"src-vf-{uid}.jpg",
            upload_source="video_frame",
            size_bytes=80,
        )
        resp = auth_client.get("/api/admin/files/stats/summary")
        by_source = resp.json()["data"]["by_source"]
        assert "avatar" in by_source
        assert "video_frame" in by_source
        assert by_source["avatar"]["count"] >= 1
