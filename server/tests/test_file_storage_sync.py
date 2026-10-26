"""147 阶段一 Step 5：路径 A 写接线 —— register 落库后同步对象存储 + 状态流转

状态机（§5.2）：
- 落库：`storage=<当前backend>`，`local` 后端直接 SYNCED（无需上传）
- `kodo`（或测试注入 `memory`）后端：PENDING → put 成功 SYNCED / 抛错 FAILED
- put 失败不阻断上传：保留行与本地文件，交补偿任务（§5.3）
"""

import os

import pytest

from app.core.config import settings
from app.models.file import (
    STORAGE_STATUS_FAILED,
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)
from app.services import file_service, file_store, storage
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


# ==================== 路径 C：register_batch 后批量同步（Step 6） ====================


def _draft(tmp_path, name: str, payload: bytes) -> "file_service.FileDraft":
    src = tmp_path / name
    src.write_bytes(payload)
    import hashlib

    return file_service.FileDraft(
        src_path=str(src),
        md5=hashlib.md5(payload).hexdigest(),
        size=len(payload),
        ext=".jpg",
        upload_source="video_frame",
        original_name=name,
    )


class TestRegisterBatchSync:
    def test_batch_marks_all_synced(self, test_db, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        drafts = [
            _draft(tmp_path, "f1.jpg", b"frame-one"),
            _draft(tmp_path, "f2.jpg", b"frame-two"),
        ]
        records = file_service.register_batch(test_db, 1, drafts)
        test_db.commit()

        assert len(records) == 2
        assert all(r.storage_status == STORAGE_STATUS_SYNCED for r in records)
        backend = storage.resolve_backend(storage.load_storage_config(test_db))
        for record in records:
            assert backend.head(record.rel_path) is not None

    def test_batch_single_failure_keeps_others_synced(self, test_db, tmp_path, monkeypatch):
        """单条 put 失败只置 FAILED，不中断整批（§9.1 幂等要求）"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        backend = storage.resolve_backend(storage.load_storage_config(test_db))
        failing_md5 = None
        drafts = [
            _draft(tmp_path, "g1.jpg", b"batch-alpha"),
            _draft(tmp_path, "g2.jpg", b"batch-beta"),
        ]
        failing_md5 = drafts[1].md5
        original_put = backend.put

        def selective_put(key, source, **kwargs):
            if failing_md5[:8] in key:
                raise StorageError("模拟单条失败")
            original_put(key, source, **kwargs)

        monkeypatch.setattr(backend, "put", selective_put)

        records = file_service.register_batch(test_db, 1, drafts)
        test_db.commit()

        by_md5 = {r.md5: r for r in records}
        assert by_md5[failing_md5].storage_status == STORAGE_STATUS_FAILED
        for md5, record in by_md5.items():
            if md5 != failing_md5:
                assert record.storage_status == STORAGE_STATUS_SYNCED


# ==================== 路径 B：分片上传（Step 6） ====================


def _md5(payload: bytes) -> str:
    import hashlib

    return hashlib.md5(payload).hexdigest()


def _upload_by_chunks(test_db, payload: bytes, *, db_arg: bool = True):
    md5 = _md5(payload)
    kwargs = dict(
        total_size=len(payload),
        chunk_size=len(payload),
        total=1,
        original_name="clip.mp4",
        ext=".mp4",
    )
    if db_arg:
        file_service.open_chunk_session(1, md5, db=test_db, **kwargs)
    else:
        file_service.open_chunk_session(1, md5, **kwargs)
    file_service.register_chunk(1, md5, 0, payload)
    return file_service.complete_chunk_upload(test_db, 1, md5=md5, size_bytes=len(payload)), md5


class TestChunkCompleteSync:
    def test_manifest_records_backend_snapshot(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        payload = b"chunk-backend-snapshot"
        md5 = _md5(payload)
        manifest = file_service.open_chunk_session(
            1,
            md5,
            db=test_db,
            total_size=len(payload),
            chunk_size=len(payload),
            total=1,
            original_name="clip.mp4",
            ext=".mp4",
        )
        assert manifest.get("backend") == "memory"

    def test_complete_uploads_and_clears_chunks(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        payload = b"chunk-complete-payload" * 10
        (record, reused), md5 = _upload_by_chunks(test_db, payload)
        test_db.commit()

        assert record.storage_status == STORAGE_STATUS_SYNCED
        assert reused is False
        backend = storage.resolve_backend(storage.load_storage_config(test_db))
        assert backend.head(record.rel_path) is not None
        # 同步成功后才清理分片（§七）
        assert not os.path.isdir(_chunk_session_dir(md5))

    def test_put_failure_keeps_chunks_and_rolls_back(self, test_db, monkeypatch):
        """S3 失败：不返回 file_id、分片原样保留（可续传），无落库行"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        backend = storage.resolve_backend(storage.load_storage_config(test_db))

        def boom(*args, **kwargs):
            raise StorageError("模拟对象存储不可用")

        monkeypatch.setattr(backend, "put", boom)

        payload = b"chunk-put-failure" * 10
        md5 = _md5(payload)
        with pytest.raises(file_service.ChunkSyncError):
            _upload_by_chunks(test_db, payload)

        assert os.path.isfile(file_store.chunk_data_abs(1, md5))  # 分片保留
        assert file_store.read_manifest(1, md5) is not None  # 会话保留
        test_db.rollback()
        from app.models.file import File

        assert test_db.query(File).filter(File.md5 == md5).count() == 0


def _chunk_session_dir(md5: str) -> str:
    from app.core.config import settings as _settings

    return os.path.join(str(_settings.UPLOAD_DIR), "tmp", "chunks", "1", md5)


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
