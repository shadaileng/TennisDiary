"""local backend：现状等价实现（落盘即真相，无外链）

- 对象键 = `files.rel_path`，物理位置由 `file_store` 解析（UPLOAD_DIR 内）
- `presign_get` 返回 `None` → 响应层回落 `rel_path` 走后端代理（§6.1）
- `backend=local` 即整套对象存储改造的回滚开关（146 §六）
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from app.services import file_store
from app.services.storage.base import StorageBackend, StorageError, StorageObject, normalize_key

_READ_CHUNK = 64 * 1024


class LocalBackend(StorageBackend):
    """把「本地受管目录」当作对象存储（语义与 S3 后端对齐）"""

    name = "local"

    def _abs_path(self, key: str) -> str | None:
        """受管绝对路径；越界/非法键返回 None（视同不存在）"""
        return file_store.resolve(normalize_key(key))

    def put(self, key: str, source: str | bytes, *, content_type: str = "") -> None:
        del content_type  # 本地文件以扩展名/探测决定 MIME，不依赖该参数
        normalized = normalize_key(key)
        if file_store.resolve(normalized) is None:
            raise StorageError(f"非法对象键（越出受管目录）: {key}")
        abs_path = file_store.abs_of(normalized)
        if isinstance(source, bytes):
            try:
                file_store.write_bytes(abs_path, source)
            except OSError as exc:
                raise StorageError(f"本地写入失败: {normalized}") from exc
            return
        src = Path(source)
        if not src.is_file():
            raise StorageError(f"源文件不存在: {source}")
        try:
            file_store.copy_into_place(str(src), abs_path)
        except OSError as exc:
            raise StorageError(f"本地写入失败: {normalized}") from exc

    def head(self, key: str) -> StorageObject | None:
        abs_path = self._abs_path(key)
        if abs_path is None:
            return None
        try:
            if not Path(abs_path).is_file():
                return None
            return StorageObject(key=normalize_key(key), size=Path(abs_path).stat().st_size)
        except OSError as exc:
            raise StorageError(f"本地读取失败: {key}") from exc

    def open_range(self, key: str, start: int = 0, end: int | None = None) -> Iterator[bytes]:
        if start < 0:
            raise ValueError(f"非法读取偏移量: {start}")
        abs_path = self._abs_path(key)
        if abs_path is None or not os.path.isfile(abs_path):
            return  # 缺失对象视同空区间（与 memory 对齐）
        try:
            with open(abs_path, "rb") as f:
                f.seek(start)
                remaining = None if end is None else max(end - start, 0)
                while remaining is None or remaining > 0:
                    size = _READ_CHUNK if remaining is None else min(_READ_CHUNK, remaining)
                    chunk = f.read(size)
                    if not chunk:
                        break
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
        except OSError as exc:
            raise StorageError(f"本地读取失败: {key}") from exc

    def delete(self, key: str) -> bool:
        normalized = (key or "").lstrip("/")
        if self._abs_path(normalized) is None:
            return False
        return file_store.unlink(normalized)

    def presign_get(self, key: str, ttl: int | None = None) -> str | None:
        del key, ttl
        return None  # 本地无外链：响应层回落 rel_path 走后端代理

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        upload_dir = Path(file_store.settings.UPLOAD_DIR)
        if not upload_dir.is_dir():
            return
        for path in sorted(upload_dir.rglob("*")):
            if not path.is_file():
                continue
            key = file_store.rel_of(str(path))
            if key.startswith(prefix):
                yield key
