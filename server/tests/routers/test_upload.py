"""POST /api/upload/avatar 头像上传接口测试"""

import io
import os

from app.core.config import settings


class TestUploadAvatar:
    """测试 /api/upload/avatar 接口"""

    def _png_bytes(self) -> bytes:
        # 最小 1x1 PNG 头部，仅用于验证存储与扩展名校验
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 8

    def test_upload_avatar_success(self, auth_client):
        """上传合法 png → 返回 url"""
        response = auth_client.post(
            "/api/upload/avatar",
            files={"file": ("avatar.png", io.BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["url"].startswith("avatars/1/")
        assert data["url"].endswith(".png")

        # 文件已落盘
        abs_path = os.path.join(settings.UPLOAD_DIR, data["url"].replace("/", os.sep))
        assert os.path.isfile(abs_path)

    def test_upload_avatar_reject_extension(self, auth_client):
        """非法扩展名（非图片）→ 400"""
        response = auth_client.post(
            "/api/upload/avatar",
            files={"file": ("evil.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_avatar_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.post(
            "/api/upload/avatar",
            files={"file": ("avatar.png", io.BytesIO(b"x"), "image/png")},
        )
        assert response.status_code in (401, 403)


class TestDownloadAvatar:
    """测试 GET /api/upload/avatar/{user_id}/{filename}（公开访问，无需鉴权）"""

    def test_download_own_avatar_success(self, auth_client):
        """先上传再下载自己的头像 → 200"""
        up = auth_client.post(
            "/api/upload/avatar",
            files={"file": ("a.png", io.BytesIO(b"\x89PNGdata"), "image/png")},
        )
        url = up.json()["data"]["url"]  # avatars/1/<uuid>.png
        filename = url.split("/")[-1]

        dl = auth_client.get(f"/api/upload/avatar/1/{filename}")
        assert dl.status_code == 200

    def test_download_other_user_avatar_denied(self, auth_client):
        """下载他人头像（文件不存在） → 404"""
        response = auth_client.get("/api/upload/avatar/999/some.png")
        assert response.status_code == 404

    def test_download_avatar_no_auth_required(self, client):
        """公开访问无需鉴权，文件不存在时返回 404"""
        response = client.get("/api/upload/avatar/1/nonexistent.png")
        assert response.status_code == 404
