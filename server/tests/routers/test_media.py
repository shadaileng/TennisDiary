"""GET /api/media/{path} 用户端媒体服务测试（归属校验 / 路径穿越 / query token）"""

import os

# ==================== 辅助 ====================


def _write(data_dir, rel_path: str, content: bytes = b"jpeg-data") -> str:
    """在隔离 UPLOAD_DIR 下写入文件，返回相对路径"""
    uploads = data_dir / "uploads"
    abs_path = uploads / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)
    return rel_path.replace(os.sep, "/")


# ==================== 归属与基础 ====================


class TestMediaOwnership:
    """媒体文件归属校验（当前用户 mock_user.id=1）"""

    def test_own_file(self, auth_client, data_dir, monkeypatch):
        """本人 videos/1/ 下文件 → 200 + image/jpeg"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        _write(data_dir, "videos/1/abc_sk0.jpg")
        response = auth_client.get("/api/media/videos/1/abc_sk0.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/jpeg")

    def test_others_forbidden(self, auth_client, data_dir, monkeypatch):
        """他人 videos/2/ 文件 → 403"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        _write(data_dir, "videos/2/abc.mp4")
        response = auth_client.get("/api/media/videos/2/abc.mp4")
        assert response.status_code == 403

    def test_video_content_type(self, auth_client, data_dir, monkeypatch):
        """mp4 → video/mp4"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        _write(data_dir, "videos/1/clip.mp4", b"mp4-bytes")
        response = auth_client.get("/api/media/videos/1/clip.mp4")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("video/mp4")

    def test_missing_file_404(self, auth_client, data_dir, monkeypatch):
        """文件不存在 → 404"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        response = auth_client.get("/api/media/videos/1/nope.jpg")
        assert response.status_code == 404

    def test_path_traversal_blocked(self, auth_client, data_dir, monkeypatch):
        """路径穿越 → 404"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        response = auth_client.get("/api/media/../.env")
        assert response.status_code == 404

    def test_requires_auth(self, client, data_dir, monkeypatch):
        """未登录 → 401/403"""
        from app.core.config import settings

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        _write(data_dir, "videos/1/abc.jpg")
        response = client.get("/api/media/videos/1/abc.jpg")
        assert response.status_code in (401, 403)


# ==================== query token 鉴权 ====================


class TestMediaQueryToken:
    """小程序 <image>/<video> 无法携带自定义头，须支持 ?token= 查询参数"""

    def test_query_token_authorizes(self, client, test_db, data_dir, monkeypatch):
        """携带合法 ?token= → 200"""
        from app.core.auth import create_access_token
        from app.core.config import settings
        from app.models.user import User

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        user = User(openid="media-openid-7", nickname="媒体用户")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        _write(data_dir, f"videos/{user.id}/frame.jpg")
        token = create_access_token(user.openid)

        response = client.get(f"/api/media/videos/{user.id}/frame.jpg?token={token}")
        assert response.status_code == 200

    def test_bad_token_rejected(self, client, test_db, data_dir, monkeypatch):
        """非法 token → 401/403"""
        from app.core.config import settings
        from app.models.user import User

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        user = User(openid="media-openid-7", nickname="媒体用户")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        _write(data_dir, f"videos/{user.id}/frame.jpg")
        response = client.get(f"/api/media/videos/{user.id}/frame.jpg?token=bogus")
        assert response.status_code in (401, 403)
