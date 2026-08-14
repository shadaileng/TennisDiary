"""Admin AI 服务商管理测试（/api/admin/config/providers）+ 配置直选解析"""

import json
from typing import ClassVar

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.ai_provider import AiProvider
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.services import config_service

PROVIDER_BODY = {
    "name": "我的服务商",
    "base_url": "https://custom.example.com/v1",
    "api_key": "sk-custom-key-1234",
    "models": ["vision-v1", "vision-pro"],
    "enabled": True,
}


@pytest.fixture(autouse=True)
def _clean_provider_state(test_db):
    """每个用例后清理服务商与配置覆盖行，避免模块级共享库互相污染"""
    yield
    test_db.query(AiProvider).delete()
    test_db.query(SystemConfig).delete()
    test_db.commit()


def _create_provider(test_db, **overrides):
    data = {**PROVIDER_BODY, **overrides}
    provider = AiProvider(
        name=data["name"],
        base_url=data["base_url"],
        api_key=data.get("api_key") or "",
        models=data["models"],
        enabled=data.get("enabled", True),
        sort_order=data.get("sort_order", 0),
    )
    test_db.add(provider)
    test_db.commit()
    test_db.refresh(provider)
    return provider


class TestProviderList:
    """GET /api/admin/config/providers"""

    def test_list_masked_and_is_selected(self, auth_client, test_db):
        """列表返回掩码 key + is_selected（被 ai.provider 选中的标记）"""
        _create_provider(test_db, name="p-a", api_key="sk-abcdef1234567890wxyz")
        _create_provider(test_db, name="p-b", api_key="sk-bbbbbbbbbbbbbbbb1234")
        config_service.set_config_value(test_db, "ai.provider", "p-b", admin_id=1)
        response = auth_client.get("/api/admin/config/providers")
        assert response.status_code == 200
        items = response.json()["data"]["providers"]
        by_name = {i["name"]: i for i in items}
        assert by_name["p-a"]["is_selected"] is False
        assert by_name["p-b"]["is_selected"] is True
        assert by_name["p-a"]["api_key"] == "sk-****wxyz"
        assert "abcdef1234567890" not in response.text

    def test_list_requires_auth(self, client, admin_token):
        """未登录 → 401"""
        client.headers.pop("X-Auth-Token", None)
        try:
            response = client.get("/api/admin/config/providers")
            assert response.status_code in (401, 403)
        finally:
            client.headers["X-Auth-Token"] = admin_token

    def test_list_forbidden_without_permission(self, client, test_db):
        """普通管理员（无 system:config）→ 403"""
        role = test_db.query(Role).filter(Role.code == "admin").first()
        admin = Admin(
            username="normal_admin",
            password_hash=hash_password("testpass123"),
            nickname="普通管理员",
            role_id=role.id,
            is_active=True,
        )
        test_db.add(admin)
        test_db.commit()
        resp = client.post(
            "/api/admin/auth/login", json={"username": "normal_admin", "password": "testpass123"}
        )
        token = resp.json()["data"]["access_token"]
        response = client.get("/api/admin/config/providers", headers={"X-Auth-Token": token})
        assert response.status_code == 403


class TestProviderCreate:
    """POST /api/admin/config/providers"""

    def test_create_success(self, auth_client, test_db):
        """新增服务商 → 返回掩码条目与模型列表，可查到明文 key"""
        response = auth_client.post("/api/admin/config/providers", json=PROVIDER_BODY)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "我的服务商"
        assert data["api_key"] == "sk-****1234"
        assert data["models"] == ["vision-v1", "vision-pro"]
        assert data["default_model"] == "vision-v1"
        assert data["is_selected"] is False
        row = test_db.query(AiProvider).filter(AiProvider.name == "我的服务商").first()
        assert row.api_key == "sk-custom-key-1234"
        assert row.models == ["vision-v1", "vision-pro"]

    def test_create_duplicate_name_400(self, auth_client, test_db):
        """name 重复 → 400"""
        _create_provider(test_db, name="dup")
        response = auth_client.post(
            "/api/admin/config/providers", json={**PROVIDER_BODY, "name": "dup"}
        )
        assert response.status_code == 400

    def test_create_invalid_url_400(self, auth_client):
        """base_url 非法 → 400"""
        response = auth_client.post(
            "/api/admin/config/providers", json={**PROVIDER_BODY, "base_url": "ftp://nope"}
        )
        assert response.status_code == 400

    def test_create_empty_models_400(self, auth_client):
        """models 为空列表 → 400/422 校验失败"""
        response = auth_client.post(
            "/api/admin/config/providers", json={**PROVIDER_BODY, "models": []}
        )
        assert response.status_code in (400, 422)

    def test_create_missing_fields_400(self, auth_client):
        """缺少必填字段 → 400/422 校验失败"""
        response = auth_client.post("/api/admin/config/providers", json={"name": "no-url"})
        assert response.status_code in (400, 422)


class TestProviderUpdate:
    """PUT /api/admin/config/providers/{pid}"""

    def test_update_fields(self, auth_client, test_db):
        """更新 base_url / models / api_key / enabled"""
        provider = _create_provider(test_db)
        response = auth_client.put(
            f"/api/admin/config/providers/{provider.id}",
            json={
                "name": provider.name,
                "base_url": "https://updated.example.com/v1",
                "api_key": "sk-updated-8888",
                "models": ["vision-v2", "vision-v3"],
                "enabled": False,
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["base_url"] == "https://updated.example.com/v1"
        assert data["models"] == ["vision-v2", "vision-v3"]
        assert data["default_model"] == "vision-v2"
        assert data["enabled"] is False
        assert data["api_key"] == "sk-****8888"

    def test_update_duplicate_name_400(self, auth_client, test_db):
        """改名与其他服务商冲突 → 400"""
        _create_provider(test_db, name="other")
        target = _create_provider(test_db, name="target")
        response = auth_client.put(
            f"/api/admin/config/providers/{target.id}", json={**PROVIDER_BODY, "name": "other"}
        )
        assert response.status_code == 400

    def test_update_unknown_404(self, auth_client):
        """未知 id → 404"""
        response = auth_client.put("/api/admin/config/providers/99999", json=PROVIDER_BODY)
        assert response.status_code == 404


class TestProviderDelete:
    """DELETE /api/admin/config/providers/{pid}"""

    def test_delete_success(self, auth_client, test_db):
        """删除自定义服务商 → 成功"""
        provider = _create_provider(test_db)
        response = auth_client.delete(f"/api/admin/config/providers/{provider.id}")
        assert response.status_code == 200
        assert test_db.query(AiProvider).filter(AiProvider.id == provider.id).first() is None

    def test_delete_selected_409(self, auth_client, test_db):
        """被 ai.provider 选中的服务商 → 409，提示先切换"""
        provider = _create_provider(test_db, name="in-use")
        config_service.set_config_value(test_db, "ai.provider", "in-use", admin_id=1)
        response = auth_client.delete(f"/api/admin/config/providers/{provider.id}")
        assert response.status_code == 409
        assert test_db.query(AiProvider).filter(AiProvider.id == provider.id).first() is not None

    def test_delete_unknown_404(self, auth_client):
        """未知 id → 404"""
        response = auth_client.delete("/api/admin/config/providers/99999")
        assert response.status_code == 404


class TestAIConfigResolution:
    """get_ai_config 引用解析"""

    def test_selected_provider_reference(self, test_db, monkeypatch):
        """选中服务商 → api_key/base_url 直读条目，model 用条目默认（列表首项）"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://env.example.com/v1")
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        _create_provider(
            test_db, name="p-ref", api_key="sk-provider-5678", models=["vision-v1", "vision-v2"]
        )
        config_service.set_config_value(test_db, "ai.provider", "p-ref", admin_id=1)

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "p-ref"
        assert cfg.api_key == "sk-provider-5678"
        assert cfg.base_url == "https://custom.example.com/v1"
        assert cfg.model == "vision-v1"

    def test_second_model_override_wins(self, test_db, monkeypatch):
        """列表第二模型通过 ai.model 覆盖后生效"""
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        _create_provider(test_db, name="p-multi", models=["vision-v1", "vision-v2"])
        config_service.set_config_value(test_db, "ai.provider", "p-multi", admin_id=1)
        config_service.set_config_value(test_db, "ai.model", "vision-v2", admin_id=1)

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "p-multi"
        assert cfg.model == "vision-v2"

    def test_model_override_wins(self, test_db, monkeypatch):
        """选中服务商后 ai.model 覆盖 > 条目默认 model"""
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        _create_provider(test_db, name="p-model", models=["vision-default", "vision-pro"])
        config_service.set_config_value(test_db, "ai.provider", "p-model", admin_id=1)
        config_service.set_config_value(test_db, "ai.model", "qwen-vl-plus", admin_id=1)

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "p-model"
        assert cfg.model == "qwen-vl-plus"

    def test_custom_falls_back_env_defaults(self, test_db, monkeypatch):
        """custom/未选择 → 独立覆盖 > 环境变量默认"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://env.example.com/v1")
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        _create_provider(test_db, name="unused", api_key="sk-unused-0000")

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "custom"
        assert cfg.api_key == "sk-env-key"
        assert cfg.base_url == "https://env.example.com/v1"
        assert cfg.model == "env-model"

    def test_custom_with_independent_overrides(self, test_db, monkeypatch):
        """custom 模式下独立覆盖生效"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://env.example.com/v1")
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        config_service.set_config_value(test_db, "ai.api_key", "sk-db-key-4321", admin_id=1)

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "custom"
        assert cfg.api_key == "sk-db-key-4321"

    def test_provider_disabled_falls_back(self, test_db, monkeypatch):
        """选中条目被禁用 → 回落 custom 语义"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        _create_provider(test_db, name="p-off", api_key="sk-off-key", enabled=False)
        config_service.set_config_value(test_db, "ai.provider", "p-off", admin_id=1)

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "custom"
        assert cfg.api_key == "sk-env-key"

    def test_provider_deleted_falls_back(self, test_db, monkeypatch):
        """选中条目被删除 → 回落 custom 语义"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        provider = _create_provider(test_db, name="p-gone", api_key="sk-gone-key")
        config_service.set_config_value(test_db, "ai.provider", "p-gone", admin_id=1)
        test_db.delete(provider)
        test_db.commit()

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "custom"
        assert cfg.api_key == "sk-env-key"

    def test_provider_empty_key_uses_override(self, test_db, monkeypatch):
        """条目 key 为空 → 回落独立覆盖/env 默认；model 仍用条目默认"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_MODEL", "env-model")
        _create_provider(test_db, name="p-nokey", api_key="", models=["vision-v1", "vision-pro"])
        config_service.set_config_value(test_db, "ai.provider", "p-nokey", admin_id=1)

        cfg = config_service.get_ai_config(test_db)
        assert cfg.provider == "p-nokey"
        assert cfg.api_key == "sk-env-key"
        assert cfg.model == "vision-v1"


class _FakeResponse:
    """模拟 httpx 响应"""

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


class _FakeClient:
    """模拟 httpx.AsyncClient：get 返回 list 响应、post 返回 probe 响应"""

    def __init__(self, list_status=404, list_text="{}", post_results=None):
        self.list_status = list_status
        self.list_text = list_text
        self.post_results = post_results or {}  # {model: (status, text)}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        return _FakeResponse(self.list_status, self.list_text)

    async def post(self, url, **kwargs):
        model = (kwargs.get("json") or {}).get("model")
        status, text = self.post_results.get(model, (404, "{}"))
        return _FakeResponse(status, text)


class _TimeoutClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        from httpx import TimeoutException

        raise TimeoutException("timeout")


class TestCheckModels:
    """POST /api/admin/config/providers/check-models 模型可用性校验"""

    CHECK_BODY: ClassVar[dict] = {
        "base_url": "https://custom.example.com/v1",
        "api_key": "sk-custom-key-1234",
        "models": ["agnes-2.5-flash", "agnes-25-flash"],
    }

    def _patch_client(self, monkeypatch, client):
        from app.routers.admin import ai_providers as router

        monkeypatch.setattr(router.httpx, "AsyncClient", lambda *a, **k: client)

    def test_list_mode_success(self, auth_client, monkeypatch):
        """GET /models 200 → list 策略：命中/未命中 + available 列表"""
        client = _FakeClient(
            list_status=200,
            list_text='{"data": [{"id": "agnes-2.5-flash"}, {"id": "agnes-2.0-flash"}]}',
        )
        self._patch_client(monkeypatch, client)

        response = auth_client.post(
            "/api/admin/config/providers/check-models", json=self.CHECK_BODY
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ok"] is True
        assert data["strategy"] == "list"
        assert data["available"] == ["agnes-2.5-flash", "agnes-2.0-flash"]
        by_model = {r["model"]: r for r in data["results"]}
        assert by_model["agnes-2.5-flash"]["ok"] is True
        assert by_model["agnes-25-flash"]["ok"] is False

    def test_list_mode_parse_models_flat(self, auth_client, monkeypatch):
        """GET /models 返回扁平字符串数组也能解析"""
        client = _FakeClient(list_status=200, list_text='{"models": ["model-a", "model-b"]}')
        self._patch_client(monkeypatch, client)

        response = auth_client.post(
            "/api/admin/config/providers/check-models",
            json={**self.CHECK_BODY, "models": ["model-a", "model-x"]},
        )
        data = response.json()["data"]
        assert data["strategy"] == "list"
        by_model = {r["model"]: r for r in data["results"]}
        assert by_model["model-a"]["ok"] is True
        assert by_model["model-x"]["ok"] is False

    def test_probe_fallback(self, auth_client, monkeypatch):
        """GET /models 404 → probe 逐模型探测（混合 200/503）"""
        client = _FakeClient(
            list_status=404,
            post_results={
                "agnes-2.5-flash": (200, '{"choices": [{"message": {"content": "ok"}}]}'),
                "agnes-25-flash": (503, '{"error": "model_not_found"}'),
            },
        )
        self._patch_client(monkeypatch, client)

        response = auth_client.post(
            "/api/admin/config/providers/check-models", json=self.CHECK_BODY
        )
        data = response.json()["data"]
        assert data["ok"] is True
        assert data["strategy"] == "probe"
        by_model = {r["model"]: r for r in data["results"]}
        assert by_model["agnes-2.5-flash"]["ok"] is True
        assert by_model["agnes-25-flash"]["ok"] is False
        assert "503" in by_model["agnes-25-flash"]["message"]

    def test_probe_fallback_unparseable_list(self, auth_client, monkeypatch):
        """GET /models 200 但无法解析模型列表 → 回落 probe"""
        client = _FakeClient(
            list_status=200,
            list_text='{"unexpected": true}',
            post_results={"agnes-2.5-flash": (200, '{"choices": []}')},
        )
        self._patch_client(monkeypatch, client)

        response = auth_client.post(
            "/api/admin/config/providers/check-models", json=self.CHECK_BODY
        )
        data = response.json()["data"]
        assert data["strategy"] == "probe"
        assert data["results"][0]["ok"] is True

    def test_auth_failure(self, auth_client, monkeypatch):
        """GET /models 401 → ok=False 鉴权失败，不再 probe"""
        client = _FakeClient(list_status=401, list_text='{"error": "Invalid API key"}')
        self._patch_client(monkeypatch, client)

        response = auth_client.post(
            "/api/admin/config/providers/check-models", json=self.CHECK_BODY
        )
        data = response.json()["data"]
        assert data["ok"] is False
        assert "鉴权" in data["message"]

    def test_timeout(self, auth_client, monkeypatch):
        """GET /models 超时 → ok=False 连接超时"""
        self._patch_client(monkeypatch, _TimeoutClient())
        response = auth_client.post(
            "/api/admin/config/providers/check-models", json=self.CHECK_BODY
        )
        data = response.json()["data"]
        assert data["ok"] is False
        assert "超时" in data["message"]

    def test_missing_base_url_422(self, auth_client):
        """base_url 为空 / models 为空 → 422"""
        response = auth_client.post(
            "/api/admin/config/providers/check-models",
            json={**self.CHECK_BODY, "base_url": ""},
        )
        assert response.status_code == 422
        response = auth_client.post(
            "/api/admin/config/providers/check-models",
            json={**self.CHECK_BODY, "models": []},
        )
        assert response.status_code == 422

    def test_forbidden_without_permission(self, client, test_db):
        """普通管理员（无 system:config）→ 403"""
        role = test_db.query(Role).filter(Role.code == "admin").first()
        admin = Admin(
            username="check_normal",
            password_hash=hash_password("testpass123"),
            nickname="普通管理员",
            role_id=role.id,
            is_active=True,
        )
        test_db.add(admin)
        test_db.commit()
        resp = client.post(
            "/api/admin/auth/login", json={"username": "check_normal", "password": "testpass123"}
        )
        token = resp.json()["data"]["access_token"]
        response = client.post(
            "/api/admin/config/providers/check-models",
            headers={"X-Auth-Token": token},
            json=self.CHECK_BODY,
        )
        assert response.status_code == 403
