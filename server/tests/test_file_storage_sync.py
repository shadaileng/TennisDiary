"""147 阶段一 Step 5：路径 A 写接线 —— register 落库后同步对象存储 + 状态流转

状态机（§5.2）：
- 落库：`storage=<当前backend>`，`local` 后端直接 SYNCED（无需上传）
- `kodo`（或测试注入 `memory`）后端：PENDING → put 成功 SYNCED / 抛错 FAILED
- put 失败不阻断上传：保留行与本地文件，交补偿任务（§5.3）
"""

import pytest

from app.core.config import settings
from app.models.file import (
    STORAGE_STATUS_FAILED,
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)
from app.services import file_service, storage
from app.services.storage import StorageConfig, StorageError

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _clean_storage_overrides(test_db):
    """清掉 storage.* 配置覆盖行，保证读到 settings（monkeypatch）默认值"""
    from app.models.system_config import SystemConfig

    test_db.query(SystemConfig).filter(SystemConfig.key.like("storage.%")).delete()
    test_db.commit()
    yield
    test_db.query(SystemConfig).filter(SystemConfig.key.like("storage.%")).delete()
    test_db.commit()
    storage.clear_backend_cache()


@pytest.fixture(autouse=True)
def _clear_backend_cache():
    storage.clear_backend_cache()
    yield
    storage.clear_backend_cache()


def _register(test_db, content: bytes = b"storage-sync-payload"):
    record, reused = file_service.register(
        test_db, 1, content=content, category="gear_image", original_name="a.jpg", ext=".jpg"
    )
    return record, reused


class TestLocalBackendPath:
    """backend=local（默认/回滚开关）：不碰对象存储，落库即 SYNCED"""

    def test_record_marked_local_synced(self, test_db):
        record, _ = _register(test_db)
        test_db.commit()
        assert record.storage == "local"
        assert record.storage_status == STORAGE_STATUS_SYNCED


class TestObjectBackendPath:
    def test_register_uploads_and_marks_synced(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        record, _ = _register(test_db, b"object-backend-payload")
        test_db.commit()

        assert record.storage == "memory"
        assert record.storage_status == STORAGE_STATUS_SYNCED

        # 同一配置快照复用同一实例 → 可直接核对对象已存在
        backend = storage.resolve_backend(storage.load_storage_config(test_db))
        assert backend.head(record.rel_path) is not None

    def test_put_failure_marks_failed_and_keeps_record(self, test_db, monkeypatch):
        """put 抛错 → FAILED + 记录保留 + 本地文件保留（交补偿，不阻断上传）"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        backend = storage.resolve_backend(storage.load_storage_config(test_db))

        def boom(*args, **kwargs):
            raise StorageError("模拟对象存储不可用")

        monkeypatch.setattr(backend, "put", boom)

        record, _ = _register(test_db, b"put-failure-payload")
        test_db.commit()

        assert record.storage_status == STORAGE_STATUS_FAILED
        assert record.id is not None  # 行保留
        assert file_service.exists(record.rel_path)  # 本地文件保留

    def test_pending_record_resyncs_on_reregister(self, test_db, monkeypatch):
        """已有记录处于 PENDING/FAILED：再次命中同 MD5 时补一次 put → SYNCED"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        record, _ = _register(test_db, b"resync-payload")
        test_db.commit()

        # 人为回退成 FAILED（模拟当时 put 失败）
        record.storage_status = STORAGE_STATUS_FAILED
        test_db.commit()

        again, reused = _register(test_db, b"resync-payload")
        test_db.commit()
        assert reused is True
        assert again.id == record.id
        assert again.storage_status == STORAGE_STATUS_SYNCED
        backend = storage.resolve_backend(storage.load_storage_config(test_db))
        assert backend.head(record.rel_path) is not None


class TestConfigSnapshot:
    def test_load_storage_config_reads_settings(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "kodo")
        monkeypatch.setattr(settings, "STORAGE_BUCKET", "bucket-x")
        monkeypatch.setattr(settings, "STORAGE_PRESIGN_TTL", 3600)
        cfg = storage.load_storage_config(test_db)
        assert cfg == StorageConfig(
            backend="kodo",
            bucket="bucket-x",
            presign_ttl=3600,
            endpoint=settings.STORAGE_ENDPOINT,
            region=settings.STORAGE_REGION,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            public_base_url=settings.STORAGE_PUBLIC_BASE_URL,
            local_retention=settings.STORAGE_LOCAL_RETENTION,
        )
        assert cfg.is_kodo is True
        assert cfg.is_local is False

    def test_same_snapshot_returns_cached_instance(self, test_db, monkeypatch):
        """配置快照 → 同一实例（kodo 客户端复用，测试可注入断言）"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        cfg = storage.load_storage_config(test_db)
        assert storage.resolve_backend(cfg) is storage.resolve_backend(cfg)

    def test_status_is_pending_before_flush_only(self, test_db):
        """列默认 PENDING 在 INSERT 前生效；同步完成后立即 SYNCED"""
        record, _ = _register(test_db, b"pending-transition")
        # register 内已 flush + 同步 → 不应停留在 PENDING
        assert record.storage_status == STORAGE_STATUS_SYNCED
        assert not (record.storage == "local" and record.storage_status == STORAGE_STATUS_PENDING)
        test_db.rollback()
        assert isinstance(File.__table__.c.storage_status.default.arg, int)
