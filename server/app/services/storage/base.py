"""StorageBackend 抽象（147 §二：对象存储统一契约）

- `files.rel_path` 同时作为对象键（前导 `/` 会被归一化去除）
- 实现方：`local`（现状等价）、`kodo`（七牛 S3 兼容）、`memory`（测试假件）
- 两态读规则（§6.1）：`presign_get` 返回绝对签名外链；返回 `None` 表示无外链，
  响应层回落 `rel_path` 走后端代理
"""

from __future__ import annotations

import abc
from collections.abc import Iterator
from dataclasses import dataclass


class StorageError(Exception):
    """对象存储操作失败（网络 / 凭据 / 源文件缺失 / 未注册后端）"""


@dataclass(frozen=True)
class StorageObject:
    """对象元数据（head 结果）"""

    key: str
    size: int
    content_type: str = ""
    etag: str = ""


def normalize_key(key: str) -> str:
    """对象键归一化：去前导 `/`、禁止空键（防路径混乱）"""
    normalized = (key or "").lstrip("/")
    if not normalized:
        raise StorageError("对象键不能为空")
    return normalized


class StorageBackend(abc.ABC):
    """对象存储后端契约

    - `put`：源为本地绝对路径或 bytes，落对象存储；失败抛 `StorageError`
    - `head`：不存在返回 `None`（不抛错）
    - `open_range`：Python 切片语义 `[start, end)`，`end` 缺省读到尾；
      不存在返回空迭代器；`start < 0` 抛 `ValueError`
    - `delete`：返回是否真的删了（幂等，缺失返回 False）
    - `presign_get`：签名外链，无外链能力的后端返回 `None`
    - `iter_keys`：按前缀列键（scan 核对用）
    """

    name: str = "abstract"

    @abc.abstractmethod
    def put(self, key: str, source: str | bytes, *, content_type: str = "") -> None:
        """上传对象（`source` 为本地绝对路径或 bytes）"""

    @abc.abstractmethod
    def head(self, key: str) -> StorageObject | None:
        """查询对象元数据，不存在返回 None"""

    @abc.abstractmethod
    def open_range(self, key: str, start: int = 0, end: int | None = None) -> Iterator[bytes]:
        """读取对象字节区间（分块迭代）"""

    @abc.abstractmethod
    def delete(self, key: str) -> bool:
        """删除对象，返回是否实际删除"""

    @abc.abstractmethod
    def presign_get(self, key: str, ttl: int | None = None) -> str | None:
        """生成签名读取外链；不支持外链的后端返回 None"""

    @abc.abstractmethod
    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        """按前缀列举对象键"""

    def exists(self, key: str) -> bool:
        """对象是否存在（`head` 便捷判定）"""
        return self.head(key) is not None
