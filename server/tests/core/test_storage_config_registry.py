"""147 阶段一 Step 3：config_registry 新增 `storage` 分类与 9 项配置"""

import pytest

from app.core.config import settings
from app.core.config_registry import (
    CONFIG_CATEGORIES,
    CONFIG_ITEMS,
    VALUE_TYPE_INT,
    VALUE_TYPE_SECRET,
    VALUE_TYPE_SELECT,
    VALUE_TYPE_URL,
    find_config_item,
)

pytestmark = pytest.mark.fast

STORAGE_KEYS = [
    "storage.backend",
    "storage.endpoint",
    "storage.region",
    "storage.bucket",
    "storage.access_key",
    "storage.secret_key",
    "storage.presign_ttl",
    "storage.public_base_url",
    "storage.local_retention",
]


class TestStorageCategory:
    def test_category_registered(self):
        keys = [c["key"] for c in CONFIG_CATEGORIES]
        assert "storage" in keys
        category = next(c for c in CONFIG_CATEGORIES if c["key"] == "storage")
        assert category["label"] == "对象存储"
        assert category["description"]

    def test_all_nine_items_registered(self):
        assert set(STORAGE_KEYS) <= {item.key for item in CONFIG_ITEMS}

    def test_all_items_editable(self):
        """9 项全部可在线配置（backend 是回滚开关，必须能改）"""
        for key in STORAGE_KEYS:
            item = find_config_item(key)
            assert item is not None, key
            assert item.editable is True, key


class TestStorageItemTypes:
    def test_backend_is_select_with_options(self):
        item = find_config_item("storage.backend")
        assert item is not None
        assert item.value_type == VALUE_TYPE_SELECT
        assert item.options == ["local", "kodo"]
        assert item.default == "local"

    def test_secrets_are_secret_type(self):
        for key in ("storage.access_key", "storage.secret_key"):
            item = find_config_item(key)
            assert item is not None
            assert item.value_type == VALUE_TYPE_SECRET

    def test_url_item(self):
        item = find_config_item("storage.public_base_url")
        assert item is not None
        assert item.value_type == VALUE_TYPE_URL

    def test_int_items_defaults(self):
        ttl = find_config_item("storage.presign_ttl")
        retention = find_config_item("storage.local_retention")
        assert ttl is not None and ttl.value_type == VALUE_TYPE_INT
        assert retention is not None and retention.value_type == VALUE_TYPE_INT
        assert ttl.default == "7200"
        assert retention.default == "0"  # 0 = 永久保留本地副本（§6.6）


class TestStorageSettingsEnv:
    """Settings 提供 env 兜底（与注册项 default 打通）"""

    def test_settings_expose_storage_attrs(self):
        for attr in (
            "STORAGE_BACKEND",
            "STORAGE_ENDPOINT",
            "STORAGE_REGION",
            "STORAGE_BUCKET",
            "STORAGE_ACCESS_KEY",
            "STORAGE_SECRET_KEY",
            "STORAGE_PRESIGN_TTL",
            "STORAGE_PUBLIC_BASE_URL",
            "STORAGE_LOCAL_RETENTION",
        ):
            assert hasattr(settings, attr), attr

    def test_settings_defaults(self):
        assert settings.STORAGE_BACKEND == "local"
        assert settings.STORAGE_PRESIGN_TTL == 7200
        assert settings.STORAGE_LOCAL_RETENTION == 0
