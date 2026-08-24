"""文件下载接口测试（B1-11）"""

import os
import time

from app.core.config import settings
from app.models.file import File


def _write_upload_file(rel_path: str, content: bytes = b"hello-world") -> str:
    """在 UPLOAD_DIR 下写入一个上传文件，返回相对路径"""
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
    return rel_path


def _create_file_record(test_db, user_id: int, rel_path: str):
    """创建文件记录（模拟上传流程创建的记录）"""
    import hashlib

    md5 = hashlib.md5(b"hello-world").hexdigest()
    file_record = File(
        user_id=user_id,
        md5=md5,
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=11,
        mime_type="image/jpeg",
        upload_source="gear_image",
        ref_count=1,
        created_at=time.time(),
    )
    test_db.add(file_record)
    test_db.commit()
    return file_record


def _create_gear(auth_client, photo: str):
    """通过接口创建一个引用 photo 的装备"""
    return auth_client.post(
        "/api/gears",
        json={
            "category": "球拍",
            "name": "Test Gear",
            "buy_date": "2026-08-05",
            "price": 100,
            "feeling": "good",
            "photo": photo,
        },
    )


def test_download_own_file(auth_client, test_db):
    """自有 File 记录引用的文件可正常下载"""
    rel = _write_upload_file("images/own.jpg")
    _create_file_record(test_db, user_id=1, rel_path=rel)

    resp = auth_client.get(f"/api/files/{rel}")
    assert resp.status_code == 200
    assert resp.content == b"hello-world"
    assert resp.headers["content-type"].startswith("image/")


def test_download_other_user_file(auth_client, test_db):
    """他人文件（File 记录不属于本人）返回 404"""
    rel = _write_upload_file("images/other.jpg")
    _create_file_record(test_db, user_id=999, rel_path=rel)

    resp = auth_client.get(f"/api/files/{rel}")
    assert resp.status_code == 404


def test_download_nonexistent_file(auth_client):
    """不存在文件返回 404"""
    resp = auth_client.get("/api/files/images/missing.jpg")
    assert resp.status_code == 404


def test_path_traversal_blocked(auth_client):
    """路径穿越应被拒绝（404）"""
    resp = auth_client.get("/api/files/../config.py")
    assert resp.status_code == 404

    resp2 = auth_client.get("/api/files/images/../../app/main.py")
    assert resp2.status_code == 404


def test_download_requires_auth(client):
    """未带 token 返回 401"""
    _write_upload_file("images/own.jpg")
    resp = client.get("/api/files/images/own.jpg")
    assert resp.status_code in (401, 403)
