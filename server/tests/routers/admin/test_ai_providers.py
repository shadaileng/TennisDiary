"""Admin AI 服务商管理测试（/api/admin/config/providers）+ 配置直选解析"""

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
