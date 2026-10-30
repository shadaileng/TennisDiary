"""存储后端工厂（`storage.backend` 即回滚开关：local / kodo / memory）"""

from __future__ import annotations

from app.services.storage.base import StorageBackend, StorageError
from app.services.storage.config import StorageConfig, load_storage_config
from app.services.storage.local import LocalBackend
from app.services.storage.memory import MemoryBackend

__all__ = ["StorageConfig", "get_backend", "load_storage_config", "resolve_backend"]

# 配置快照 → 后端实例缓存（同快照复用同一实例：kodo 客户端只建一次，
# 测试可用同一实例注入/断言）。配置变更会得到新快照 → 自然新建实例。
_BACKEND_CACHE: dict[StorageConfig, StorageBackend] = {}


def resolve_backend(config: StorageConfig | None = None) -> StorageBackend:
    """按配置快照构造后端实例（不读 DB、不建网络连接）

    - `local`：现状等价实现（回滚开关）
    - `kodo`：七牛 S3 兼容（客户端懒构造，配置缺失在首次使用时报错）
    - `memory`：测试注入件（不出现在配置页下拉，仅供测试/单测路由）
    """
    cfg = config or StorageConfig()
    cached = _BACKEND_CACHE.get(cfg)
    if cached is not None:
        return cached
    if cfg.backend == "local":
        backend: StorageBackend = LocalBackend()
    elif cfg.backend == "memory":
        backend = MemoryBackend()
    elif cfg.backend == "kodo":
        from app.services.storage.kodo import KodoBackend

        backend = KodoBackend(cfg)
    else:
        raise StorageError(f"未知存储后端: {cfg.backend}")
    _BACKEND_CACHE[cfg] = backend
    return backend


def clear_backend_cache() -> None:
    """清空实例缓存（配置变更后强制重建 / 测试隔离）"""
    _BACKEND_CACHE.clear()


def get_backend(db) -> StorageBackend:
    """读配置快照并返回后端（请求/管线开工时调用一次）"""
    return resolve_backend(load_storage_config(db))
