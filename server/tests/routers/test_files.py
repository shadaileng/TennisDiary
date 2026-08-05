"""文件下载接口测试（B1-11）"""

import os

from app.core.config import settings


def _write_upload_file(rel_path: str, content: bytes = b"hello-world") -> str:
    """在 UPLOAD_DIR 下写入一个上传文件，返回相对路径"""
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
    return rel_path


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


def test_download_own_file(auth_client):
    """自有 Gear 引用的文件可正常下载"""
    rel = _write_upload_file("images/own.jpg")
    _create_gear(auth_client, rel)

    resp = auth_client.get(f"/api/files/{rel}")
    assert resp.status_code == 200
    assert resp.content == b"hello-world"
    assert resp.headers["content-type"].startswith("image/")


def test_download_other_user_file(auth_client, test_db):
    """他人文件（未在本人 Gear 中引用）返回 404"""
    import time

    from app.models.gear import Gear

    rel = _write_upload_file("images/other.jpg")
    # 创建一个引用该路径但属于其他 user_id 的 gear
    g = Gear(
        user_id=999,
        category="x",
        name="other",
        buy_date="",
        price=0,
        feeling="",
        photo=rel,
        created_at=time.time(),
    )
    test_db.add(g)
    test_db.commit()

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
