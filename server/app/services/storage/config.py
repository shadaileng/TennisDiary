"""存储配置快照（147 §四 `storage.*` 九项）

- 生效值：DB 覆盖（system_configs）> env 默认，读取走 `config_service`
- **配置快照**：一次请求/一个管线开工时取一次（146 §3.4 约束 4），进行中不重读
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

# 默认值与 config_registry 注册项保持一致（key 未注册时的兜底）
_DEFAULT_BACKEND = "local"
_DEFAULT_PRESIGN_TTL = 7200
_DEFAULT_LOCAL_RETENTION = 0


@dataclass(frozen=True)
class StorageConfig:
    """对象存储生效配置快照（纯数据，可安全跨层传递）"""

    backend: str = _DEFAULT_BACKEND
    endpoint: str = ""
    region: str = ""
    bucket: str = ""
    access_key: str = ""
    secret_key: str = ""
    presign_ttl: int = _DEFAULT_PRESIGN_TTL
    public_base_url: str = ""
    local_retention: int = _DEFAULT_LOCAL_RETENTION

    @property
    def is_kodo(self) -> bool:
        return self.backend == "kodo"

    @property
    def is_local(self) -> bool:
        return self.backend == "local"


def _int_or(value: str, fallback: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def load_storage_config(db: Session) -> StorageConfig:
    """读取九项 `storage.*` 配置（DB 覆盖 > env 默认），返回快照

    配置项未注册（Step 3 之前）或值非法时按默认值兜底，保证任何阶段都可用。
    """
    from app.services.config_service import get_config_value

    return StorageConfig(
        backend=get_config_value(db, "storage.backend") or _DEFAULT_BACKEND,
        endpoint=get_config_value(db, "storage.endpoint"),
        region=get_config_value(db, "storage.region"),
        bucket=get_config_value(db, "storage.bucket"),
        access_key=get_config_value(db, "storage.access_key"),
        secret_key=get_config_value(db, "storage.secret_key"),
        presign_ttl=_int_or(get_config_value(db, "storage.presign_ttl"), _DEFAULT_PRESIGN_TTL),
        public_base_url=get_config_value(db, "storage.public_base_url"),
        local_retention=_int_or(
            get_config_value(db, "storage.local_retention"), _DEFAULT_LOCAL_RETENTION
        ),
    )
