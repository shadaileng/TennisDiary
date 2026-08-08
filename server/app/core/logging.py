"""基于 loguru 的统一日志系统

双输出：控制台（sys.stderr）+ 文件（LOG_DIR/LOG_FILE），
支持级别过滤、按大小滚动切割、按时间保留。

日志分离：
- admin.log：后台管理API日志
- user.log：小程序API日志
- app.log：通用日志（保留兼容）

模块在 import 时即调用 setup_logging()，保证任何模块
`from app.core.logging import logger` 拿到的都是已配置好的 logger。
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings

# JSON格式化模板（结构化日志）
JSON_FORMAT = (
    '{"time":"{time:YYYY-MM-DDTHH:mm:ss.SSS}","level":"{level}",'
    '"module":"{module}","function":"{function}","line":{line},'
    '"message":"{message}","source":"{extra[source]}"'
)


def setup_logging() -> None:
    """幂等初始化日志（先 remove 再 add，避免重复 handler）"""
    logger.remove()

    # 确保日志目录存在
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 选择格式：JSON或传统格式
    use_json = settings.LOG_JSON_ENABLED
    file_format = JSON_FORMAT if use_json else settings.LOG_FORMAT

    # 控制台输出（便于容器 stdio 采集）
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        colorize=not use_json,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # 通用日志文件（app.log）
    logger.add(
        f"{settings.LOG_DIR}/{settings.LOG_FILE}",
        level=settings.LOG_LEVEL,
        format=file_format,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # 管理后台日志（admin.log）
    logger.add(
        f"{settings.LOG_DIR}/{settings.LOG_ADMIN_FILE}",
        level=settings.LOG_LEVEL,
        format=file_format,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
        filter=lambda record: record["extra"].get("source") == "admin",
    )

    # 小程序API日志（user.log）
    logger.add(
        f"{settings.LOG_DIR}/{settings.LOG_USER_FILE}",
        level=settings.LOG_LEVEL,
        format=file_format,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
        filter=lambda record: record["extra"].get("source") == "user",
    )


# 创建带source的logger绑定
def get_logger(source: str = "app"):
    """获取带source标识的logger"""
    return logger.bind(source=source)


# 默认logger（source=app）
logger = logger.bind(source="app")

setup_logging()
