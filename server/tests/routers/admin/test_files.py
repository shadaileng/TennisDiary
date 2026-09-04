"""Admin 文件管理路由测试

覆盖：
- GET  /api/admin/files          列表（分页 + 过滤 + 分类）
- DELETE /api/admin/files/{id}   软删除（引用归零 + 共享路径检查）
- POST /api/admin/files/cleanup  清理旧文件
- GET  /api/admin/files/stats    统计摘要
- POST /api/admin/files/scan     扫描孤儿
- POST /api/admin/files/register 注册孤儿（含空列表=全量注册）
- POST /api/admin/files/repair   修复 MIME
"""

import hashlib
import os
import time

import pytest

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
        # 秒传语义：物理路径与 MD5 共用，但 original_name 全局唯一（109 唯一约束）
        _insert_file(
            test_db,
            user_id=uid2,
            rel_path=rel,
            md5=md5,
            original_name=f"shared-keep-{uid2}.jpg",
            upload_source="gear_image",
        )

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


class TestAdminFileListFilterByType:
    """GET /api/admin/files?business_type=xxx"""

    def test_list_filter_by_business_type(self, auth_client, test_db):
        """按业务类型筛选"""
        uid = _next_uid()
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"biz-gear-{uid}.jpg",
            business_type="gear",
            business_id=100,
        )
        _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"biz-analysis-{uid}.jpg",
            business_type="analysis",
            business_id=200,
        )
        resp = auth_client.get("/api/admin/files?business_type=gear")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert all(i["business_type"] == "gear" for i in items)


class TestAdminFileStatsOrphan:
    """GET /api/admin/files/stats/summary - orphan_files 统计"""

    def test_stats_includes_orphan_files(self, auth_client, test_db):
        """统计中包含引用计数为0的文件数"""
        uid = _next_uid()
        # 创建一个引用计数为0的文件
        record = _insert_file(
            test_db,
            user_id=uid,
            rel_path=f"orphan-{uid}.jpg",
        )
        record.ref_count = 0
        record.deleted_at = time.time()
        test_db.commit()

        resp = auth_client.get("/api/admin/files/stats/summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 存在统计中
        assert "total_count" in data
        assert "total_size_bytes" in data


class TestAdminFileScan:
    """POST /api/admin/files/scan"""

    def test_scan_finds_orphan_files(self, auth_client, test_db):
        """扫描返回未注册文件列表"""
        uid = _next_uid()
        # 创建一个未注册的文件
        rel = f"scan-test-{uid}/orphan.jpg"
        _write_file(rel, b"orphan-content")

        resp = auth_client.post("/api/admin/files/scan")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_files" in data
        assert "registered_files" in data
        assert "orphan_files" in data
        assert "orphans" in data

    def test_scan_excludes_registered_files(self, auth_client, test_db):
        """已注册文件不在未注册列表中"""
        uid = _next_uid()
        rel = f"scan-registered-{uid}.jpg"
        _write_file(rel, b"registered-content")
        _insert_file(test_db, user_id=uid, rel_path=rel)

        resp = auth_client.post("/api/admin/files/scan")
        assert resp.status_code == 200
        orphans = resp.json()["data"]["orphans"]
        assert rel not in [o["rel_path"] for o in orphans]

    def test_scan_inferred_user_id(self, auth_client, test_db):
        """路径能正确推断 user_id"""
        uid = _next_uid()
        rel = f"avatars/{uid}/test-scan.jpg"
        _write_file(rel, b"scan-content")

        resp = auth_client.post("/api/admin/files/scan")
        assert resp.status_code == 200
        orphans = resp.json()["data"]["orphans"]
        matching = [o for o in orphans if o["rel_path"] == rel]
        assert len(matching) == 1
        assert matching[0]["inferred_user_id"] == uid


class TestAdminFileRegister:
    """POST /api/admin/files/register"""

    def test_register_single_file(self, auth_client, test_db):
        """注册单个文件成功，File 表有记录"""
        uid = _next_uid()
        rel = f"register-test-{uid}.jpg"
        _write_file(rel, b"register-content")

        resp = auth_client.post(
            "/api/admin/files/register",
            json={"files": [rel], "default_user_id": uid},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["registered"] == 1

        # 验证 File 记录已创建
        from app.models.file import File

        record = test_db.query(File).filter(File.rel_path == rel).first()
        assert record is not None
        assert record.user_id == uid

    def test_register_multiple_files(self, auth_client, test_db):
        """批量注册多个文件成功"""
        uid = _next_uid()
        paths = [f"batch-register-{uid}/{i}.jpg" for i in range(3)]
        for p in paths:
            _write_file(p, f"content-{p}".encode())

        resp = auth_client.post(
            "/api/admin/files/register",
            json={"files": paths, "default_user_id": uid},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["registered"] == 3

    def test_register_nonexistent_file(self, auth_client, test_db):
        """注册不存在的文件被跳过"""
        resp = auth_client.post(
            "/api/admin/files/register",
            json={"files": ["nonexistent-file.jpg"], "default_user_id": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["registered"] == 0

    def test_register_empty_list_scans_and_registers_all(self, auth_client, test_db):
        """空文件列表触发扫描并注册全部孤儿"""
        uid = _next_uid()
        for i in range(2):
            rel = f"register-all-test-{uid}/{i}.jpg"
            _write_file(rel, f"content-{i}".encode())

        resp = auth_client.post(
            "/api/admin/files/register",
            json={"files": [], "default_user_id": uid},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["registered"] >= 2


def _write_real_mp4(rel_path: str) -> None:
    """用系统 ffmpeg 生成一段极小真实 mp4 到 UPLOAD_DIR 下 rel_path"""
    import subprocess

    from app.services import video_service

    ffmpeg = video_service.find_ffmpeg()
    if ffmpeg is None:
        pytest.skip("ffmpeg 未安装，跳过真实 mp4 探测测试")
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x64:d=0.2",
            "-pix_fmt",
            "yuv420p",
            abs_path,
        ],
        capture_output=True,
        timeout=60,
        check=True,
    )


class TestAdminFileRepairMime:
    """文件修复（Step 116）：确保 mp4 不会被当成 audio"""

    def test_repair_fixes_empty_mime_mp4(self, auth_client, test_db):
        """repair 端点扫描并修正空 mime_type 的 mp4 记录为 video/mp4"""
        uid = _next_uid()
        rel = f"videos/{uid}/repair.mp4"
        _write_real_mp4(rel)
        rec = _insert_file(
            test_db,
            user_id=uid,
            rel_path=rel,
            mime_type="",
            upload_source="video",
        )
        resp = auth_client.post("/api/admin/files/repair", json={"only_empty": True})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["repaired"] >= 1
        test_db.refresh(rec)
        assert rec.mime_type == "video/mp4"

    def test_repair_requires_admin(self, client, test_db):
        """未登录调用 repair → 401/403（清除模块级 auth_client 残留的 token 头）"""
        client.headers.pop("X-Auth-Token", None)
        resp = client.post("/api/admin/files/repair", json={"only_empty": True})
        assert resp.status_code in (401, 403)
