"""日志系统单元测试"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from loguru import logger

from app.core.logging import setup_logging


@pytest.fixture(autouse=True)
def clean_logger_handlers():
    """测试前清空 handler，避免相互影响"""
    logger.remove()
    yield
    logger.remove()


@pytest.fixture
def log_settings(tmp_path, monkeypatch):
    """将日志目录指向临时目录，避免污染真实磁盘"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOG_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "LOG_FILE", "app.log")
    return settings


def test_setup_logging_adds_handlers(log_settings):
    """setup_logging 后 handler 数量 >= 2（控制台 + 文件）"""
    setup_logging()
    assert len(logger._core.handlers) >= 2


def test_log_file_created(log_settings):
    """初始化后日志文件被创建"""
    setup_logging()
    log_path = os.path.join(log_settings.LOG_DIR, log_settings.LOG_FILE)
    assert os.path.exists(log_path)


def test_logger_sink_to_file(log_settings):
    """日志内容写入文件"""
    setup_logging()
    logger.info("hello loguru test")
    logger.complete()

    log_path = os.path.join(log_settings.LOG_DIR, log_settings.LOG_FILE)
    with open(log_path, encoding="utf-8") as f:
        content = f.read()
    assert "hello loguru test" in content


def test_rotation_config_applied(log_settings):
    """文件 handler 启用了按大小滚动与按时间保留机制"""
    setup_logging()
    # 遍历所有 handler，找到 FileSink（文件输出）并断言滚动/保留机制已启用
    file_sinks = [
        h._sink for h in logger._core.handlers.values() if h._sink.__class__.__name__ == "FileSink"
    ]
    assert file_sinks, "应至少有一个文件输出 handler"
    for sink in file_sinks:
        # rotation/retention 编译为 partial 函数即表示机制已配置
        assert sink._rotation_function is not None
        assert sink._retention_function is not None


def test_idempotent(log_settings):
    """连续调用 setup_logging 两次，handler 数量不翻倍"""
    setup_logging()
    count_before = len(logger._core.handlers)
    setup_logging()
    count_after = len(logger._core.handlers)
    assert count_after == count_before


def test_auth_router_logs_login(log_settings, client, test_db):
    """登录成功时鉴权路由会写日志"""
    setup_logging()

    with patch(
        "app.routers.auth.code_to_openid",
        new=AsyncMock(return_value="wx_openid_log_test"),
    ):
        resp = client.post("/api/auth/login", json={"code": "valid_code_log"})

    assert resp.status_code == 200
    logger.complete()

    log_path = os.path.join(log_settings.LOG_DIR, log_settings.LOG_FILE)
    with open(log_path, encoding="utf-8") as f:
        content = f.read()
    assert "微信登录成功" in content
