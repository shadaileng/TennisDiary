"""进程池管理：为 CPU 密集型操作（ffmpeg/MediaPipe）提供进程池"""

from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

log = get_logger("process_pool")

# 全局进程池单例
_process_pool: ProcessPoolExecutor | None = None


def get_process_pool() -> ProcessPoolExecutor:
    """获取或创建全局进程池（惰性初始化）"""
    global _process_pool
    if _process_pool is None:
        import os

        # 最多 4 个 worker，避免过度占用 CPU
        max_workers = min(os.cpu_count() or 1, 4)
        _process_pool = ProcessPoolExecutor(max_workers=max_workers)
        log.info("进程池已初始化", max_workers=max_workers)
    return _process_pool


def shutdown_process_pool() -> None:
    """关闭进程池（应用退出时调用）"""
    global _process_pool
    if _process_pool is not None:
        _process_pool.shutdown(wait=False)
        _process_pool = None
        log.info("进程池已关闭")


def get_pool_status() -> dict:
    """获取进程池运行状态（供 Admin 监控）"""
    pool = get_process_pool()
    return {
        "max_workers": pool._max_workers,
        "queue_size": pool._work_queue.qsize() if hasattr(pool, "_work_queue") else 0,
    }
