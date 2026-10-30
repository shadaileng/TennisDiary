"""kodo backend：七牛 Kodo 的 S3 兼容接口（boto3）

- 凭据/endpoint 取配置快照（§四 `storage.*`），客户端**懒构造**（首次使用时）
- 私有 bucket + 签名外链（§6.1）：`presign_get` 生成限时 GET URL
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from app.services.storage.base import StorageBackend, StorageError, StorageObject, normalize_key
from app.services.storage.config import StorageConfig

_READ_CHUNK = 64 * 1024
_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound", "NoSuchBucket"}


def _error_code(exc: Exception) -> str:
    """从 botocore 异常里取 Error.Code（非 botocore 异常返回空串）"""
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            return str(error.get("Code", ""))
    return ""


class KodoBackend(StorageBackend):
    """七牛 Kodo（S3 兼容）后端"""

    name = "kodo"

    def __init__(self, config: StorageConfig) -> None:
        self._config = config
        self._client = None

    # ---------- 客户端 ----------

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self):
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:  # pragma: no cover - 依赖缺失属部署事故
            raise StorageError("boto3 未安装，无法启用对象存储后端") from exc

        cfg = self._config
        missing = [
            name
            for name, value in (
                ("endpoint", cfg.endpoint),
                ("bucket", cfg.bucket),
                ("access_key", cfg.access_key),
                ("secret_key", cfg.secret_key),
            )
            if not value
        ]
        if missing:
            raise StorageError(f"对象存储配置不完整: {', '.join(missing)}")

        return boto3.client(
            "s3",
            endpoint_url=cfg.endpoint,
            region_name=cfg.region or None,
            aws_access_key_id=cfg.access_key,
            aws_secret_access_key=cfg.secret_key,
            config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 2}),
        )

    # ---------- 契约实现 ----------

    def put(self, key: str, source: str | bytes, *, content_type: str = "") -> None:
        normalized = normalize_key(key)
        extra = {"ContentType": content_type} if content_type else {}
        try:
            if isinstance(source, bytes):
                self.client.put_object(
                    Bucket=self._config.bucket, Key=normalized, Body=source, **extra
                )
                return
            if not Path(source).is_file():
                raise StorageError(f"源文件不存在: {source}")
            if extra:
                self.client.upload_file(
                    str(source), self._config.bucket, normalized, ExtraArgs=extra
                )
            else:
                self.client.upload_file(str(source), self._config.bucket, normalized)
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"对象存储写入失败: {normalized}") from exc

    def head(self, key: str) -> StorageObject | None:
        normalized = normalize_key(key)
        try:
            response = self.client.head_object(Bucket=self._config.bucket, Key=normalized)
        except Exception as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                return None
            raise StorageError(f"对象存储查询失败: {normalized}") from exc
        return StorageObject(
            key=normalized,
            size=int(response.get("ContentLength", 0)),
            content_type=str(response.get("ContentType", "")),
            etag=str(response.get("ETag", "")).strip('"'),
        )

    def open_range(self, key: str, start: int = 0, end: int | None = None) -> Iterator[bytes]:
        if start < 0:
            raise ValueError(f"非法读取偏移量: {start}")
        normalized = normalize_key(key)
        # HTTP Range 闭区间 [start, end-1]；end 缺省读到尾
        range_header = f"bytes={start}-" if end is None else f"bytes={start}-{max(end - 1, start)}"
        try:
            response = self.client.get_object(
                Bucket=self._config.bucket, Key=normalized, Range=range_header
            )
            body = response["Body"]
            try:
                yield from body.iter_chunks(_READ_CHUNK)
            finally:
                body.close()
        except StorageError:
            raise
        except Exception as exc:
            code = _error_code(exc)
            if code in _NOT_FOUND_CODES or code == "InvalidRange":
                return  # 缺失或越界 Range 视同空区间（与 local/memory 对齐）
            raise StorageError(f"对象存储读取失败: {normalized}") from exc

    def delete(self, key: str) -> bool:
        normalized = normalize_key(key)
        if self.head(normalized) is None:
            return False
        try:
            self.client.delete_object(Bucket=self._config.bucket, Key=normalized)
        except Exception as exc:
            raise StorageError(f"对象存储删除失败: {normalized}") from exc
        return True

    def presign_get(self, key: str, ttl: int | None = None) -> str | None:
        normalized = normalize_key(key)
        expires = int(ttl or self._config.presign_ttl or 7200)
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._config.bucket, "Key": normalized},
                ExpiresIn=expires,
            )
        except Exception as exc:
            raise StorageError(f"签名外链生成失败: {normalized}") from exc

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._config.bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    yield str(item["Key"])
        except Exception as exc:
            raise StorageError(f"对象存储列键失败: prefix={prefix}") from exc
