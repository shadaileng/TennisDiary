"""Admin 动态配置接口测试（/api/admin/config）"""

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.config_registry import find_config_item
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.services import config_service


@pytest.fixture(autouse=True)
def _clean_config_rows(test_db):
    """每个用例后清理 system_configs 覆盖行，避免模块级共享库互相污染"""
    yield
    test_db.query(SystemConfig).delete()
    test_db.commit()


class TestConfigList:
    """GET /api/admin/config 全量配置列表"""

    def test_list_structure(self, auth_client):
        """返回 summary / categories / items，每项字段齐全"""
        response = auth_client.get("/api/admin/config")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "summary" in data
        assert "items" in data
        assert data["summary"]["total"] == len(data["items"])
        assert any(c["key"] == "ai" for c in data["summary"]["categories"])
        item = next(i for i in data["items"] if i["key"] == "ai.base_url")
        assert item["category"] == "ai"
        assert item["label"]
        assert item["value_type"] == "url"
        assert item["editable"] is True
        assert item["source"] == "env"
        assert "value" in item
        assert "default_value" in item
        assert "options" in item

    def test_ai_items_editable(self, auth_client):
        """AI 三件套可编辑"""
        response = auth_client.get("/api/admin/config")
        items = response.json()["data"]["items"]
        keys = {i["key"]: i for i in items}
        assert keys["ai.api_key"]["editable"] is True
        assert keys["ai.api_key"]["value_type"] == "secret"
        assert keys["ai.base_url"]["editable"] is True
        assert keys["ai.model"]["editable"] is True

    def test_builtin_readonly_items(self, auth_client):
        """内置只读项：ai.timeout / ai.temperature 不可编辑、source=builtin"""
        response = auth_client.get("/api/admin/config")
        items = {i["key"]: i for i in response.json()["data"]["items"]}
        assert items["ai.timeout"]["editable"] is False
        assert items["ai.timeout"]["source"] == "builtin"
        assert items["ai.temperature"]["editable"] is False
        assert items["ai.temperature"]["source"] == "builtin"

    def test_secret_masked_no_plaintext(self, auth_client, monkeypatch):
        """secret 项 value 与 default_value 均为掩码，明文不回传"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-abcdef1234567890wxyz")
        response = auth_client.get("/api/admin/config")
        assert response.status_code == 200
        text = response.text
        assert "abcdef1234567890" not in text
        items = {i["key"]: i for i in response.json()["data"]["items"]}
        assert items["ai.api_key"]["default_value"] == "sk-****wxyz"

    def test_covers_all_settings_categories(self, auth_client):
        """注册表覆盖主要分类：app / auth / wx / ai / data / pose / log"""
        response = auth_client.get("/api/admin/config")
        cats = {c["key"] for c in response.json()["data"]["summary"]["categories"]}
        assert {"app", "auth", "wx", "ai", "data", "pose", "log"} <= cats

    def test_ai_provider_dynamic_options(self, auth_client, test_db):
        """ai.provider 为可编辑 select，options 动态 = 已维护服务商 + custom"""
        from app.models.ai_provider import AiProvider

        test_db.add(
            AiProvider(
                name="p-dyn",
                base_url="https://dyn.example.com/v1",
                api_key="sk-dyn",
                models=["vision-v1", "vision-pro"],
                enabled=True,
            )
        )
        test_db.commit()
        response = auth_client.get("/api/admin/config")
        items = {i["key"]: i for i in response.json()["data"]["items"]}
        assert items["ai.provider"]["editable"] is True
        assert items["ai.provider"]["value_type"] == "select"
        assert set(items["ai.provider"]["options"]) == {"custom", "p-dyn"}


class TestConfigUpdate:
    """PUT /api/admin/config/{key}"""

    def test_update_overrides(self, auth_client, test_db, monkeypatch):
        """设置覆盖值 → source=db、掩码正确、生效值更新"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        response = auth_client.put(
            "/api/admin/config/ai.api_key", json={"value": "sk-new-secret-1234"}
        )
        assert response.status_code == 200
        item = response.json()["data"]
        assert item["source"] == "db"
        assert item["value"] == "sk-****1234"
        assert config_service.get_config_value(test_db, "ai.api_key") == "sk-new-secret-1234"

    def test_update_secret_empty_keeps(self, auth_client, test_db, monkeypatch):
        """secret 空值 = 保持不变，不产生覆盖行"""
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        response = auth_client.put("/api/admin/config/ai.api_key", json={"value": ""})
        assert response.status_code == 200
        assert response.json()["data"]["source"] == "env"
        assert config_service.get_config_value(test_db, "ai.api_key") == "sk-env-key"

    def test_update_equal_default_normalizes(self, auth_client, test_db, monkeypatch):
        """覆盖值等于环境默认值 → 删行归一化回 env"""
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://default.example.com/v1")
        auth_client.put(
            "/api/admin/config/ai.base_url", json={"value": "https://custom.example.com/v1"}
        )
        response = auth_client.put(
            "/api/admin/config/ai.base_url", json={"value": "https://default.example.com/v1"}
        )
        assert response.json()["data"]["source"] == "env"
        assert (
            config_service.get_config_value(test_db, "ai.base_url")
            == "https://default.example.com/v1"
        )
        assert test_db.query(SystemConfig).filter(SystemConfig.key == "ai.base_url").first() is None

    def test_update_unknown_key_404(self, auth_client):
        """未知 key → 404"""
        response = auth_client.put("/api/admin/config/ai.nope", json={"value": "x"})
        assert response.status_code == 404

    def test_update_non_editable_403(self, auth_client):
        """不可编辑项 → 403"""
        response = auth_client.put("/api/admin/config/ai.timeout", json={"value": "200"})
        assert response.status_code == 403

    def test_update_invalid_url_400(self, auth_client):
        """非法 url → 400"""
        response = auth_client.put("/api/admin/config/ai.base_url", json={"value": "ftp://nope"})
        assert response.status_code == 400

    def test_update_select_non_editable_403(self, auth_client):
        """select 项（log.level）为只读 → 403"""
        response = auth_client.put("/api/admin/config/log.level", json={"value": "WARNING"})
        assert response.status_code == 403

    def test_update_bool_non_editable_403(self, auth_client):
        """bool 项（app.debug）为只读 → 403"""
        response = auth_client.put("/api/admin/config/app.debug", json={"value": "true"})
        assert response.status_code == 403

    def test_validate_select_invalid_400(self):
        """select 项非法取值 → 400（服务层校验）"""
        item = find_config_item("log.level")
        with pytest.raises(HTTPException) as exc:
            config_service._validate_value(item, "BOGUS")
        assert exc.value.status_code == 400

    def test_validate_select_valid(self):
        """select 项合法取值通过"""
        item = find_config_item("log.level")
        assert config_service._validate_value(item, "INFO") == "INFO"

    def test_validate_bool_normalized(self):
        """bool 项 true/false 归一化"""
        item = find_config_item("app.debug")
        assert config_service._validate_value(item, "TRUE") == "true"
        assert config_service._validate_value(item, "0") == "false"
        with pytest.raises(HTTPException) as exc:
            config_service._validate_value(item, "maybe")
        assert exc.value.status_code == 400

    def test_validate_int_normalized(self):
        """int 项数值校验"""
        item = find_config_item("auth.jwt_expiration_hours")
        assert config_service._validate_value(item, "24") == "24"
        with pytest.raises(HTTPException) as exc:
            config_service._validate_value(item, "abc")
        assert exc.value.status_code == 400


class TestConfigDelete:
    """DELETE /api/admin/config/{key} + POST /reset"""

    def test_delete_override(self, auth_client, test_db, monkeypatch):
        """删除覆盖行 → 恢复默认"""
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://default.example.com/v1")
        auth_client.put(
            "/api/admin/config/ai.base_url", json={"value": "https://custom.example.com/v1"}
        )
        response = auth_client.delete("/api/admin/config/ai.base_url")
        assert response.status_code == 200
        assert response.json()["data"]["source"] == "env"
        assert (
            config_service.get_config_value(test_db, "ai.base_url")
            == "https://default.example.com/v1"
        )

    def test_delete_unknown_key_404(self, auth_client):
        """未知 key → 404"""
        response = auth_client.delete("/api/admin/config/ai.nope")
        assert response.status_code == 404

    def test_reset_all(self, auth_client, test_db):
        """全部恢复默认 → 无覆盖行"""
        auth_client.put("/api/admin/config/ai.model", json={"value": "custom-model"})
        auth_client.put("/api/admin/config/app.debug", json={"value": "false"})
        response = auth_client.post("/api/admin/config/reset")
        assert response.status_code == 200
        assert test_db.query(SystemConfig).count() == 0


class TestConfigPermissions:
    """权限控制"""

    def test_requires_auth(self, client, admin_token):
        """未登录 → 401"""
        client.headers.pop("X-Auth-Token", None)
        try:
            response = client.get("/api/admin/config")
            assert response.status_code in (401, 403)
        finally:
            client.headers["X-Auth-Token"] = admin_token

    def test_forbidden_without_permission(self, client, test_db):
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
        response = client.get("/api/admin/config", headers={"X-Auth-Token": token})
        assert response.status_code == 403
