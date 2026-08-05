"""基于 loguru 的统一日志系统

双输出：控制台（sys.stderr）+ 文件（LOG_DIR/LOG_FILE），
支持级别过滤、按大小滚动切割、按时间保留。

模块在 import 时即调用 setup_logging()，保证任何模块
`from app.core.logging import logger` 拿到的都是已配置好的 logger。
"""

import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """幂等初始化日志（先 remove 再 add，避免重复 handler）"""
    logger.remove()

    # 控制台输出（便于容器 stdio 采集）
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # 文件输出（按大小滚动 + 按时间保留）
    logger.add(
        f"{settings.LOG_DIR}/{settings.LOG_FILE}",
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )


setup_logging()
