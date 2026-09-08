"""POST /api/upload/avatar 头像上传接口测试 + /api/upload/check 秒传预检"""

import io
import os
from unittest.mock import patch

from app.core.config import settings
from app.models.file import File
from app.services import file_service
from app.services.content_security import ContentSecurityError


class TestUploadAvatar:
    """测试 /api/upload/avatar 接口"""

    def _png_bytes(self) -> bytes:
        # 最小 1x1 PNG 头部，仅用于验证存储与扩展名校验
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 8

    @patch("app.routers.upload.check_image_sync", return_value=True)
    def test_upload_avatar_success(self, _mock_check, auth_client):
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

    @patch("app.routers.upload.check_image_sync", return_value=True)
    def test_upload_avatar_stores_image_mime(self, _mock_check, auth_client, test_db):
        """上传头像后 File 记录的 mime_type 为正确的 image/png（Step 116：不再为空）"""
        response = auth_client.post(
            "/api/upload/avatar",
            files={"file": ("avatar.png", io.BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 200
        url = response.json()["data"]["url"]
        rec = test_db.query(File).filter(File.rel_path == url).first()
        assert rec is not None
        # 即便客户端未带 Content-Type，也应落正确类型
        assert rec.mime_type == "image/png"

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

    @patch("app.routers.upload.check_image_sync", return_value=True)
    def test_download_own_avatar_success(self, _mock_check, auth_client):
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


class TestUploadCheck:
    """POST /api/upload/check 秒传预检（137 阶段一 Step 2）

    覆盖：未命中 / 命中且安全 / 命中未过检 / category 来源隔离 / size 一致性 /
    物理文件缺失 / 未登录。
    """

    @staticmethod
    def _register(
        test_db,
        content: bytes = b"check-content-137",
        category: str = "video",
        ext: str = ".mp4",
        security: bool = True,
        user_id: int = 1,
    ):
        record, _ = file_service.register(
            db=test_db,
            user_id=user_id,
            content=content,
            category=category,
            original_name=f"clip{ext}",
            ext=ext,
        )
        if security:
            file_service.mark_security_checked(test_db, user_id, record.rel_path, True)
        test_db.commit()
        return record

    def _check(self, client, md5: str, size_bytes: int, category: str | None = None):
        payload = {"md5": md5, "size_bytes": size_bytes}
        if category:
            payload["category"] = category
        return client.post("/api/upload/check", json=payload)

    def test_miss_when_no_record(self, auth_client):
        resp = self._check(auth_client, "0" * 32, 1024)
        assert resp.status_code == 200
        assert resp.json()["data"]["hit"] is False

    def test_hit_and_safe_returns_url_and_file_id(self, auth_client, test_db):
        content = b"hit-safe-137"
        record = self._register(test_db, content=content, security=True)
        resp = self._check(auth_client, file_service.md5_of(content=content), len(content))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hit"] is True
        assert data["safe"] is True
        assert data["url"] == record.rel_path
        assert data["file_id"] == record.id

    def test_hit_but_unchecked_returns_safe_false(self, auth_client, test_db):
        content = b"hit-unsafe-137"
        record = self._register(test_db, content=content, security=False)
        resp = self._check(auth_client, file_service.md5_of(content=content), len(content))
        data = resp.json()["data"]
        assert data["hit"] is True
        assert data["safe"] is False
        assert data["url"] is None
        assert data["file_id"] == record.id

    def test_category_isolates_sources(self, auth_client, test_db):
        """avatar 记录按 video 预检必须 miss，按 avatar 预检命中"""
        content = b"category-isolation-137"
        self._register(test_db, content=content, category="avatar", ext=".png")
        md5 = file_service.md5_of(content=content)

        assert self._check(auth_client, md5, len(content), "video").json()["data"]["hit"] is False
        assert self._check(auth_client, md5, len(content), "avatar").json()["data"]["hit"] is True

    def test_without_category_keeps_legacy_behavior(self, auth_client, test_db):
        """不传 category：命中任意来源（向后兼容）"""
        content = b"legacy-check-137"
        self._register(test_db, content=content, category="avatar", ext=".png")
        md5 = file_service.md5_of(content=content)

        assert self._check(auth_client, md5, len(content)).json()["data"]["hit"] is True

    def test_size_mismatch_is_miss(self, auth_client, test_db):
        content = b"size-mismatch-137"
        self._register(test_db, content=content)
        md5 = file_service.md5_of(content=content)

        assert self._check(auth_client, md5, len(content) + 1).json()["data"]["hit"] is False
        assert self._check(auth_client, md5, len(content)).json()["data"]["hit"] is True

    def test_zero_size_skips_size_check(self, auth_client, test_db):
        """取不到 size（0）时不参与校验，避免误判 miss"""
        content = b"zero-size-137"
        self._register(test_db, content=content)
        md5 = file_service.md5_of(content=content)

        assert self._check(auth_client, md5, 0).json()["data"]["hit"] is True

    def test_missing_physical_file_is_miss(self, auth_client, test_db):
        content = b"missing-physical-137"
        record = self._register(test_db, content=content)
        file_service.unlink(record.rel_path)
        md5 = file_service.md5_of(content=content)

        assert self._check(auth_client, md5, len(content)).json()["data"]["hit"] is False

    def test_requires_auth(self, client):
        resp = client.post("/api/upload/check", json={"md5": "0" * 32, "size_bytes": 1})
        assert resp.status_code in (401, 403)


class TestGuestGearCheck:
    """测试 POST /api/upload/guest-gear-check（游客装备封面「仅检即弃」，免鉴权）

    不真调微信：mock code_to_openid 与 check_image_sync。断言通过/违规/fail-open/
    无效 code/非法扩展名，并确认临时文件不残留（不落盘）。
    """

    def _png_bytes(self) -> bytes:
        # 最小 PNG 头，仅用于校验扩展名与检查链路
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 8

    def _assert_no_tmp_leftover(self) -> None:
        tmp_dir = os.path.join(settings.UPLOAD_DIR, "check_tmp")
        if os.path.isdir(tmp_dir):
            assert os.listdir(tmp_dir) == []

    @patch("app.routers.upload.code_to_openid", return_value="o_openid_guest_0001")
    @patch("app.routers.upload.check_image_sync", return_value=True)
    def test_guest_check_safe_without_auth(self, _mock_check, _mock_openid, client):
        """未登录游客上传合规封面 → 200 {safe:true}，不落盘"""
        response = client.post(
            "/api/upload/guest-gear-check",
            data={"code": "wx_code_guest_001"},
            files={"file": ("g.png", io.BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 200
        assert response.json()["data"]["safe"] is True
        _mock_openid.assert_called_once_with("wx_code_guest_001")
        _mock_check.assert_called_once()
        self._assert_no_tmp_leftover()

    @patch("app.routers.upload.code_to_openid", return_value="o_openid_guest_0001")
    @patch(
        "app.routers.upload.check_image_sync",
        side_effect=ContentSecurityError(87014, "内容可能包含违规信息"),
    )
    def test_guest_check_reject_unsafe(self, _mock_check, _mock_openid, client):
        """违规封面 → 400，临时文件被清理"""
        response = client.post(
            "/api/upload/guest-gear-check",
            data={"code": "wx_code_guest_001"},
            files={"file": ("g.png", io.BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 400
        # 违规即拦截：body 结构由全局异常处理器决定，这里只断言拦截状态与不落盘
        _mock_check.assert_called_once()
        self._assert_no_tmp_leftover()

    @patch("app.routers.upload.code_to_openid", side_effect=ValueError("invalid code"))
    def test_guest_check_invalid_code(self, _mock_openid, client):
        """wx.login code 无效 → 400"""
        response = client.post(
            "/api/upload/guest-gear-check",
            data={"code": "bad_code"},
            files={"file": ("g.png", io.BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 400
        _mock_openid.assert_called_once_with("bad_code")

    @patch("app.routers.upload.code_to_openid", return_value="o_openid_guest_0001")
    @patch("app.routers.upload.check_image_sync", side_effect=RuntimeError("network down"))
    def test_guest_check_fail_open(self, _mock_check, _mock_openid, client):
        """微信/网络异常 → 200 {code:50001, success:false} 前端据此拒绝保存"""
        response = client.post(
            "/api/upload/guest-gear-check",
            data={"code": "wx_code_guest_001"},
            files={"file": ("g.png", io.BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 50001
        assert data["success"] is False
        assert data["data"] is None
        self._assert_no_tmp_leftover()

    def test_guest_check_reject_extension(self, client):
        """非法扩展名 → 400，不触发 code 换取"""
        response = client.post(
            "/api/upload/guest-gear-check",
            data={"code": "wx_code_guest_001"},
            files={"file": ("evil.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 400
