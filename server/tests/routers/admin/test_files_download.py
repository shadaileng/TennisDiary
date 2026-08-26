"""Admin 文件下载与预览路由测试

覆盖：
- GET /api/admin/files/{id}/download   完整下载 + Range 分片下载
- GET /api/admin/files/{id}/preview    预览信息
"""

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
    return 6000 + _next_seq()


def _write_file(rel_path: str, content: bytes = b"test-content") -> str:
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
    return rel_path


def _insert_file(test_db, user_id=None, rel_path=None, **overrides) -> File:
    seq = _next_seq()
    if user_id is None:
        user_id = _next_uid()
    if rel_path is None:
        rel_path = f"dl-test/{user_id}/file-{seq}.bin"
    defaults = dict(
        user_id=user_id,
        md5=f"md5-{seq}",
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=12,
        mime_type="application/octet-stream",
        upload_source="other",
        ref_count=1,
        created_at=time.time(),
    )
    defaults.update(overrides)
    record = File(**defaults)
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


class TestDownloadFile:
    """GET /api/admin/files/{id}/download"""

    def test_download_full(self, auth_client, test_db):
        content = b"hello-download-12345"
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, size_bytes=len(content))
        _write_file(rec.rel_path, content)

        resp = auth_client.get(f"/api/admin/files/{rec.id}/download")
        assert resp.status_code == 200
        assert resp.content == content
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_download_range(self, auth_client, test_db):
        content = b"0123456789abcdef"  # 16 bytes
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, size_bytes=len(content))
        _write_file(rec.rel_path, content)

        resp = auth_client.get(
            f"/api/admin/files/{rec.id}/download",
            headers={"Range": "bytes=4-9"},
        )
        assert resp.status_code == 206
        assert resp.content == b"456789"
        assert "bytes 4-9/16" in resp.headers.get("content-range", "")

    def test_download_range_from_start(self, auth_client, test_db):
        content = b"abcdefghij"  # 10 bytes
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, size_bytes=len(content))
        _write_file(rec.rel_path, content)

        resp = auth_client.get(
            f"/api/admin/files/{rec.id}/download",
            headers={"Range": "bytes=0-3"},
        )
        assert resp.status_code == 206
        assert resp.content == b"abcd"

    def test_download_range_suffix(self, auth_client, test_db):
        content = b"0123456789"  # 10 bytes
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, size_bytes=len(content))
        _write_file(rec.rel_path, content)

        resp = auth_client.get(
            f"/api/admin/files/{rec.id}/download",
            headers={"Range": "bytes=-4"},
        )
        assert resp.status_code == 206
        assert resp.content == b"6789"

    def test_download_not_found(self, auth_client, test_db):
        resp = auth_client.get("/api/admin/files/999999/download")
        assert resp.status_code == 404

    def test_download_file_not_on_disk(self, auth_client, test_db):
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, rel_path=f"missing-{uid}.bin")
        # 不写入物理文件
        resp = auth_client.get(f"/api/admin/files/{rec.id}/download")
        assert resp.status_code == 404

    def test_download_range_out_of_bounds(self, auth_client, test_db):
        content = b"abc"
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, size_bytes=len(content))
        _write_file(rec.rel_path, content)

        resp = auth_client.get(
            f"/api/admin/files/{rec.id}/download",
            headers={"Range": "bytes=10-20"},
        )
        assert resp.status_code == 416


class TestPreviewFile:
    """GET /api/admin/files/{id}/preview"""

    def test_preview_info(self, auth_client, test_db):
        uid = _next_uid()
        content = b"preview-content"
        rec = _insert_file(
            test_db,
            user_id=uid,
            original_name="photo.jpg",
            mime_type="image/jpeg",
            size_bytes=len(content),
        )
        _write_file(rec.rel_path, content)

        resp = auth_client.get(f"/api/admin/files/{rec.id}/preview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == rec.id
        assert data["mime_type"] == "image/jpeg"
        assert data["original_name"] == "photo.jpg"
        assert data["size_bytes"] == len(content)
        assert "preview_url" in data

    def test_preview_not_found(self, auth_client, test_db):
        resp = auth_client.get("/api/admin/files/999999/preview")
        assert resp.status_code == 404

    def test_preview_mime_type_fallback(self, auth_client, test_db):
        """mime_type 为空时，从文件扩展名推断"""
        uid = _next_uid()
        rec = _insert_file(
            test_db,
            user_id=uid,
            original_name="photo.jpg",
            mime_type="",
        )
        _write_file(rec.rel_path, b"fake-image")

        resp = auth_client.get(f"/api/admin/files/{rec.id}/preview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["mime_type"] == "image/jpeg"

    def test_preview_file_not_on_disk(self, auth_client, test_db):
        uid = _next_uid()
        rec = _insert_file(test_db, user_id=uid, rel_path=f"no-disk-{uid}.bin")
        resp = auth_client.get(f"/api/admin/files/{rec.id}/preview")
        assert resp.status_code == 404
