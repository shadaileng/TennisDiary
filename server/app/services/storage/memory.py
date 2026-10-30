"""内存假 backend：单测注入件（路由 / 同步服务无需真实对象存储）"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from app.services.storage.base import StorageBackend, StorageError, StorageObject, normalize_key

_READ_CHUNK = 64 * 1024


class MemoryBackend(StorageBackend):
    """进程内字典存储，行为与真实后端同一契约"""

    name = "memory"

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, source: str | bytes, *, content_type: str = "") -> None:
        del content_type  # 内存实现不保留 content-type
        normalized = normalize_key(key)
        if isinstance(source, bytes):
            self._objects[normalized] = source
            return
        try:
            self._objects[normalized] = Path(source).read_bytes()
        except OSError as exc:
            raise StorageError(f"读取源文件失败: {source}") from exc

    def head(self, key: str) -> StorageObject | None:
        normalized = (key or "").lstrip("/")
        data = self._objects.get(normalized)
        if data is None:
            return None
        return StorageObject(key=normalized, size=len(data))

    def open_range(self, key: str, start: int = 0, end: int | None = None) -> Iterator[bytes]:
        if start < 0:
            raise ValueError(f"非法读取偏移量: {start}")
        data = self._objects.get((key or "").lstrip("/"))
        if not data:
            return
        stop = len(data) if end is None else min(end, len(data))
        chunk = data[start:stop]
        for offset in range(0, len(chunk), _READ_CHUNK):
            yield chunk[offset : offset + _READ_CHUNK]

    def delete(self, key: str) -> bool:
        return self._objects.pop((key or "").lstrip("/"), None) is not None

    def presign_get(self, key: str, ttl: int | None = None) -> str | None:
        normalized = normalize_key(key)
        return f"https://memory.invalid/{normalized}?expires={ttl or 0}"

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        for key in sorted(self._objects):
            if key.startswith(prefix):
                yield key
