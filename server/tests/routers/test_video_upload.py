"""POST /api/upload/video 视频上传端点测试（137 阶段一 Step 3）

覆盖：成功上传并置 security_checked / 返回 file_id / 重复上传 mirage 且不新增记录 /
非法类型 400 / 空文件 400 / 未登录 401。
"""

import io
import os

from app.core.config import settings
from app.models.file import File
from app.services import file_service

VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


class TestUploadVideo:
    @staticmethod
    def _upload(client, filename="clip.mp4", content=VIDEO_BYTES, content_type="video/mp4"):
        return client.post(
            "/api/upload/video",
            files={"file": (filename, io.BytesIO(content), content_type)},
        )

    def test_upload_success_marks_security_checked(self, auth_client, test_db):
        resp = self._upload(auth_client)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["url"].startswith("videos/1/")
        assert data["url"].endswith(".mp4")
        assert data["mirage"] is False
        assert data["file_id"] > 0

        record = test_db.query(File).filter(File.id == data["file_id"]).first()
        assert record is not None
        assert record.upload_source == "video"
        # 137 决策 3：视频无官方检测能力，上传阶段直接视为放行
        assert record.security_checked == 1

    def test_upload_persists_file_on_disk(self, auth_client):
        data = self._upload(auth_client).json()["data"]
        abs_path = os.path.join(settings.UPLOAD_DIR, data["url"].replace("/", os.sep))
        assert os.path.isfile(abs_path)

    def test_repeat_upload_returns_mirage_without_new_record(self, auth_client, test_db):
        first = self._upload(auth_client).json()["data"]
        second = self._upload(auth_client).json()["data"]

        assert first["mirage"] is False
        assert second["mirage"] is True
        assert second["file_id"] == first["file_id"]

        total = (
            test_db.query(File)
            .filter(File.user_id == 1, File.upload_source == "video", File.deleted_at.is_(None))
            .count()
        )
        assert total == 1

    def test_reject_non_video_extension(self, auth_client):
        resp = self._upload(
            auth_client,
            filename="note.txt",
            content=b"hello",
            content_type="text/plain",
        )
        assert resp.status_code == 400

    def test_accept_video_content_type_without_extension(self, auth_client):
        """扩展名缺失但 content-type 为 video/* → 放行，后缀兜底 .mp4"""
        resp = self._upload(auth_client, filename="clip", content_type="video/mp4")
        assert resp.status_code == 200
        assert resp.json()["data"]["url"].endswith(".mp4")

    def test_reject_empty_file(self, auth_client):
        resp = self._upload(auth_client, content=b"")
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = self._upload(client)
        assert resp.status_code in (401, 403)

    def test_uploaded_file_hits_check_endpoint(self, auth_client, test_db):
        """上传后按 video 分类预检应当命中且 safe（两步链路闭环）"""
        data = self._upload(auth_client).json()["data"]
        record = file_service.find_by_id(test_db, 1, data["file_id"])
        assert record is not None

        resp = auth_client.post(
            "/api/upload/check",
            json={
                "md5": record.md5,
                "size_bytes": record.size_bytes,
                "category": "video",
            },
        )
        assert resp.status_code == 200
        checked = resp.json()["data"]
        assert checked["hit"] is True
        assert checked["safe"] is True
        assert checked["file_id"] == data["file_id"]
