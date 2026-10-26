"""对象存储抽象层（147 阶段一）

对外统一入口：

```python
from app.services import storage

backend = storage.get_backend(db)          # 读配置快照构造后端
backend.put(rel_path, local_abs_path)      # 写对象存储
url = backend.presign_get(rel_path)        # 签名外链（None → 回落代理）
```

- `StorageBackend`：契约（put/head/open_range/delete/presign/iter_keys）
- `LocalBackend` / `KodoBackend` / `MemoryBackend`：三实现
- `StorageConfig` + `load_storage_config`：配置快照
- `resolve_backend` / `get_backend`：工厂（backend 即回滚开关）
"""

from app.services.storage.base import StorageBackend, StorageError, StorageObject
from app.services.storage.config import StorageConfig, load_storage_config
from app.services.storage.factory import clear_backend_cache, get_backend, resolve_backend
from app.services.storage.local import LocalBackend
from app.services.storage.memory import MemoryBackend

__all__ = [
    "LocalBackend",
    "MemoryBackend",
    "StorageBackend",
    "StorageConfig",
    "StorageError",
    "StorageObject",
    "clear_backend_cache",
    "get_backend",
    "load_storage_config",
    "resolve_backend",
]


def __getattr__(name: str):
    """KodoBackend 懒加载：避免非 kodo 场景付出 boto3 导入成本"""
    if name == "KodoBackend":
        from app.services.storage.kodo import KodoBackend

        return KodoBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
