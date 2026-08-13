"""AI 网关状态监控 + Admin 静态文件服务测试"""

import json
from pathlib import Path

from app.core.config import settings


class TestAiStatus:
    """GET /api/admin/system/ai-status 三件套状态探测"""

    def test_ai_status_returns_fields(self, auth_client):
        """返回 ai / ffmpeg / mediapipe / pose_model / summary 结构"""
        response = auth_client.get("/api/admin/system/ai-status")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "ai" in data
        assert "ffmpeg" in data
        assert "mediapipe" in data
        assert "pose_model" in data
        assert "summary" in data

    def test_ai_status_without_key(self, auth_client, monkeypatch):
        """未配置 AI Key → configured=False，key_masked 为空串"""
        monkeypatch.setattr(settings, "AI_API_KEY", "")
        data = auth_client.get("/api/admin/system/ai-status").json()["data"]
        assert data["ai"]["configured"] is False
        assert data["ai"]["key_masked"] == ""
        assert data["ai"]["model"] == settings.AI_MODEL
        assert data["ai"]["base_url"] == settings.AI_BASE_URL

    def test_ai_status_key_masked(self, auth_client, monkeypatch):
        """配置 Key → 仅返回掩码 sk-****{末尾4位}，不暴露明文"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-abcdef1234567890wxyz")
        data = auth_client.get("/api/admin/system/ai-status").json()["data"]
        assert data["ai"]["configured"] is True
        assert data["ai"]["key_masked"] == "sk-****wxyz"
        assert "abcdef1234567890" not in data["ai"]["key_masked"]

    def test_ffmpeg_and_mediapipe_booleans(self, auth_client):
        """ffmpeg.available / mediapipe.available 均为布尔值"""
        data = auth_client.get("/api/admin/system/ai-status").json()["data"]
        assert isinstance(data["ffmpeg"]["available"], bool)
        assert isinstance(data["mediapipe"]["available"], bool)
        assert isinstance(data["pose_model"]["available"], bool)

    def test_pose_model_missing_flag(self, auth_client, monkeypatch):
        """姿态模型缺失 → available=False 且 summary.missing 包含 pose_model"""
        monkeypatch.setattr(settings, "POSE_MODEL_PATH", "/nonexistent/model.task")
        data = auth_client.get("/api/admin/system/ai-status").json()["data"]
        assert data["pose_model"]["available"] is False
        assert "pose_model" in data["summary"]["missing"]


class TestAiConnect:
    """GET /api/admin/system/ai-connect AI 连通性测试"""

    def test_connect_success(self, auth_client, monkeypatch):
        """服务端代理 GET {AI_BASE_URL}/models 成功 → ok=True"""
        from app.routers import admin  # noqa: F401
        from app.routers.admin import system as system_router

        class FakeResponse:
            status_code = 200
            text = '{"data": [{"id": "qwen-vl-max"}]}'

            def json(self):
                return json.loads(self.text)

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(system_router.httpx, "AsyncClient", FakeClient)
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-test")
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://example.com/v1")

        response = auth_client.get("/api/admin/system/ai-connect")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ok"] is True
        assert data["status_code"] == 200
        assert "models" in data["url"]

    def test_connect_no_key(self, auth_client, monkeypatch):
        """未配置 Key → 不发起网络请求，ok=False"""
        monkeypatch.setattr(settings, "AI_API_KEY", "")
        response = auth_client.get("/api/admin/system/ai-connect")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ok"] is False
        assert "key" in str(data["message"]).lower() or "未配置" in data["message"]

    def test_connect_server_error(self, auth_client, monkeypatch):
        """上游非 200 → ok=False 且带回状态码"""
        from app.routers.admin import system as system_router

        class FakeResponse:
            status_code = 401
            text = '{"error": {"message": "Invalid API key"}}'

            def json(self):
                return json.loads(self.text)

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(system_router.httpx, "AsyncClient", FakeClient)
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-bad")
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://example.com/v1")

        response = auth_client.get("/api/admin/system/ai-connect")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ok"] is False
        assert data["status_code"] == 401


class TestAdminStaticFiles:
    """GET /api/admin/system/files/{path} 静态文件服务"""

    def test_serve_file(self, auth_client, data_dir):
        """正常读取 UPLOAD_DIR 内图片 → 200 + 正确 content-type"""
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / "analyses" / "cover.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"\xff\xd8\xff\xe0fakejpeg")

        response = auth_client.get("/api/admin/system/files/analyses/cover.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == b"\xff\xd8\xff\xe0fakejpeg"

    def test_serve_file_not_found(self, auth_client, data_dir):
        """文件不存在 → 404"""
        response = auth_client.get("/api/admin/system/files/missing/nope.jpg")
        assert response.status_code == 404

    def test_serve_file_traversal_rejected(self, auth_client, data_dir):
        """路径穿越（../）→ 404"""
        response = auth_client.get("/api/admin/system/files/../secret.txt")
        assert response.status_code == 404

    def test_serve_file_encoded_traversal_rejected(self, auth_client, data_dir):
        """URL 编码路径穿越（..%2F）→ 404"""
        response = auth_client.get("/api/admin/system/files/..%2Fsecret.txt")
        assert response.status_code == 404

    def test_serve_file_absolute_inside_rejected(self, auth_client, data_dir):
        """指向 DATA_DIR 根部的绝对路径（../../）→ 404"""
        response = auth_client.get("/api/admin/system/files/../../secret.txt")
        assert response.status_code == 404

    def test_serve_file_requires_auth(self, client, data_dir):
        """未登录 → 401/403"""
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / "cover.jpg"
        target.write_bytes(b"jpg")
        client.headers.pop("X-Auth-Token", None)  # auth_client 已给共享 client 注入 token，先清除
        response = client.get("/api/admin/system/files/cover.jpg")
        assert response.status_code in (401, 403)
