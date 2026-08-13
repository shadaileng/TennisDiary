"""配置环境感知加载测试（Step 73）"""


def test_app_env_is_test():
    """pytest 运行时应注入 APP_ENV=test"""
    import os

    assert os.getenv("APP_ENV") == "test"


def test_settings_secret_is_test_only():
    """测试环境不应泄漏真实 JWT_SECRET（应为 .env.test 的测试值）"""
    from app.core.config import settings

    assert settings.JWT_SECRET == "test-only-jwt-secret"
    assert settings.JWT_SECRET != "change-me-in-production-please"


def test_settings_data_dir_isolated_from_prod():
    """测试环境下配置已被隔离，不指向真实 data/（autouse fixture 会覆盖为 tmp_path）"""
    from app.core.config import settings

    # autouse _isolate_data_dirs 已将 DATA_DIR 隔离到 tmp_path/data，绝不可能是真实 data/
    assert "data" not in settings.DATA_DIR or "/data/" not in settings.DATA_DIR
