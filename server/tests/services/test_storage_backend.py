"""147 阶段一 Step 1/2：StorageBackend 抽象契约（内存假件 + local 实现 + 工厂）

契约（§二）：put / head / open_range / delete / presign / iter_keys。
- 内存假 backend（MemoryBackend）：后续 storage_sync_service、路由接线的测试注入件
- local backend：现状等价实现（落盘即真相，无外链）
- 工厂 resolve_backend(StorageConfig)：纯函数，backend 即回滚开关
"""

import os

import pytest

from app.services.storage import (
    LocalBackend,
    MemoryBackend,
    StorageBackend,
    StorageConfig,
    StorageError,
    resolve_backend,
)

pytestmark = pytest.mark.fast

KEY = "avatars/1/d41d8cd98f00b204e9800998ecf8427e.png"
CONTENT = b"hello storage world"


# ==================== 契约：内存假件与 local 实现共用同一组断言 ====================


class TestBackendContract:
    """同一套契约跑 MemoryBackend 与 LocalBackend（parametrize）"""

    @pytest.fixture(params=["memory", "local"])
    def backend(self, request) -> StorageBackend:
        if request.param == "memory":
            return MemoryBackend()
        return LocalBackend()

    def test_put_head_bytes_roundtrip(self, backend: StorageBackend):
        backend.put(KEY, CONTENT)
        obj = backend.head(KEY)
        assert obj is not None
        assert obj.key == KEY
        assert obj.size == len(CONTENT)

    def test_put_from_local_file(self, backend: StorageBackend, tmp_path):
        src = tmp_path / "src.bin"
        src.write_bytes(CONTENT)
        backend.put(KEY, str(src))
        obj = backend.head(KEY)
        assert obj is not None and obj.size == len(CONTENT)

    def test_put_overwrites_existing(self, backend: StorageBackend):
        backend.put(KEY, b"old-content")
        backend.put(KEY, b"new")
        obj = backend.head(KEY)
        assert obj is not None and obj.size == 3

    def test_head_missing_returns_none(self, backend: StorageBackend):
        assert backend.head("nope/missing.bin") is None

    def test_open_range_slice(self, backend: StorageBackend):
        backend.put(KEY, CONTENT)
        assert b"".join(backend.open_range(KEY, 0, 5)) == CONTENT[:5]
        assert b"".join(backend.open_range(KEY, 6)) == CONTENT[6:]
        assert b"".join(backend.open_range(KEY)) == CONTENT

    def test_open_range_end_beyond_size_clamps(self, backend: StorageBackend):
        backend.put(KEY, CONTENT)
        assert b"".join(backend.open_range(KEY, 0, 10_000)) == CONTENT

    def test_open_range_negative_start_raises(self, backend: StorageBackend):
        backend.put(KEY, CONTENT)
        with pytest.raises(ValueError):
            list(backend.open_range(KEY, -1))

    def test_open_range_missing_key_returns_empty(self, backend: StorageBackend):
        assert b"".join(backend.open_range("nope/missing.bin", 0, 4)) == b""

    def test_delete_removes_object(self, backend: StorageBackend):
        backend.put(KEY, CONTENT)
        assert backend.delete(KEY) is True
        assert backend.head(KEY) is None

    def test_delete_missing_is_idempotent(self, backend: StorageBackend):
        assert backend.delete("nope/missing.bin") is False

    def test_key_normalization_strips_leading_slash(self, backend: StorageBackend):
        backend.put("/" + KEY, CONTENT)
        assert backend.head(KEY) is not None
        assert backend.delete("/" + KEY) is True

    def test_iter_keys_by_prefix(self, backend: StorageBackend):
        backend.put("avatars/1/a.png", b"a")
        backend.put("avatars/2/b.png", b"b")
        backend.put("gear_images/3/c.png", b"c")
        assert sorted(backend.iter_keys("avatars/")) == [
            "avatars/1/a.png",
            "avatars/2/b.png",
        ]

    def test_put_missing_source_raises_storage_error(self, backend: StorageBackend, tmp_path):
        with pytest.raises(StorageError):
            backend.put(KEY, str(tmp_path / "not-exists.bin"))

    def test_is_abstract_cannot_instantiate_bare(self):
        with pytest.raises(TypeError):
            StorageBackend()  # type: ignore[abstract]


# ==================== presign：两态规则的关键差异 ====================


class TestPresign:
    def test_memory_backend_returns_signed_url_with_key(self):
        backend = MemoryBackend()
        backend.put(KEY, CONTENT)
        url = backend.presign_get(KEY, ttl=7200)
        assert url.startswith("https://")
        assert KEY in url

    def test_local_backend_returns_none_fallback_to_proxy(self):
        """local 无外链：返回 None → 响应层回落 rel_path（§6.1 两态规则）"""
        backend = LocalBackend()
        backend.put(KEY, CONTENT)
        assert backend.presign_get(KEY) is None

    def test_local_backend_none_for_missing_key(self):
        assert LocalBackend().presign_get("nope/missing.bin") is None


# ==================== 工厂与配置快照（backend = 回滚开关） ====================


class TestResolveBackend:
    def test_default_is_local(self):
        assert isinstance(resolve_backend(StorageConfig()), LocalBackend)

    def test_resolve_local(self):
        assert isinstance(resolve_backend(StorageConfig(backend="local")), LocalBackend)

    def test_resolve_memory(self):
        """memory 仅供测试注入（路由/同步服务单测无需真实对象存储）"""
        assert isinstance(resolve_backend(StorageConfig(backend="memory")), MemoryBackend)

    def test_resolve_kodo(self):
        from app.services.storage import KodoBackend

        backend = resolve_backend(
            StorageConfig(
                backend="kodo",
                endpoint="https://s3.fake-region.qiniucs.com",
                region="fake-region",
                bucket="test-bucket",
                access_key="ak",
                secret_key="sk",
            )
        )
        assert isinstance(backend, KodoBackend)

    def test_resolve_unknown_backend_raises(self):
        with pytest.raises(StorageError):
            resolve_backend(StorageConfig(backend="cos"))


class TestStorageConfig:
    def test_defaults(self):
        cfg = StorageConfig()
        assert cfg.backend == "local"
        assert cfg.presign_ttl == 7200
        assert cfg.local_retention == 0
        assert cfg.public_base_url == ""

    def test_local_retention_zero_means_keep_forever(self):
        assert StorageConfig(local_retention=0).local_retention == 0


class TestLocalBackendPaths:
    """local backend 必须读写 UPLOAD_DIR 受管路径（file_store 解析）"""

    def test_put_writes_under_upload_dir(self):
        from app.services import file_store

        backend = LocalBackend()
        backend.put(KEY, CONTENT)
        abs_path = file_store.abs_of(KEY)
        assert os.path.isfile(abs_path)
        with open(abs_path, "rb") as f:
            assert f.read() == CONTENT
