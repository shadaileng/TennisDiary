"""存储配置快照（147 §四 `storage.*` 九项）

- 生效值：DB 覆盖（system_configs）> env 默认，读取走 `config_service` 同一套语义
- **配置快照**：一次请求/一个管线开工时取一次（146 §3.4 约束 4），进行中不重读
- 批量一次 `IN` 查询（而非 9 次逐 key 查询）：读路径（响应层外链）每请求都会取快照
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

# 注册表中的九个 key（顺序无关，仅用于批量取覆盖值）
STORAGE_CONFIG_KEYS: tuple[str, ...] = (
    "storage.backend",
    "storage.endpoint",
    "storage.region",
    "storage.bucket",
    "storage.access_key",
    "storage.secret_key",
    "storage.presign_ttl",
    "storage.public_base_url",
    "storage.local_retention",
)

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

    与 `config_service.get_config_value` 同一套语义（有覆盖行取覆盖值，否则取注册项
    默认），但**一次 `IN` 查询批量取回**，避免响应层每条外链都打 9 次配置查询。

    配置项未注册（Step 3 之前）或值非法时按默认值兜底，保证任何阶段都可用。
    """
    from app.core.config_registry import find_config_item
    from app.models.system_config import SystemConfig

    overrides: dict[str, str | None] = {}
    if db is not None:
        rows = (
            db.query(SystemConfig.key, SystemConfig.value)
            .filter(SystemConfig.key.in_(STORAGE_CONFIG_KEYS))
            .all()
        )
        overrides = {key: value for key, value in rows}

    def effective(key: str) -> str:
        value = overrides.get(key, None)
        if value is not None:
            return value
        item = find_config_item(key)
        return item.default if item is not None else ""

    return StorageConfig(
        backend=effective("storage.backend") or _DEFAULT_BACKEND,
        endpoint=effective("storage.endpoint"),
        region=effective("storage.region"),
        bucket=effective("storage.bucket"),
        access_key=effective("storage.access_key"),
        secret_key=effective("storage.secret_key"),
        presign_ttl=_int_or(effective("storage.presign_ttl"), _DEFAULT_PRESIGN_TTL),
        public_base_url=effective("storage.public_base_url"),
        local_retention=_int_or(effective("storage.local_retention"), _DEFAULT_LOCAL_RETENTION),
    )
