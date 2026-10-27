"""147 阶段一 Step 10：补偿任务三触发点 + 存量迁移 CLI

§5.3 补偿任务（不引入常驻线程，复用 139 兜底范式）：

1. **启动时**：`run_startup_compensation` 扫一次超时 `PENDING/FAILED`（lifespan 调
   `schedule_startup_compensation` 丢线程池一次性执行）
2. **请求内顺带**：上传成功后 `compensate_after_upload` 重传同用户超时 `FAILED`
3. **Admin 手动**：`POST /files/sync scope=failed`（Step 8 已覆盖）

扫描条件：`storage_status IN (0,2) AND created_at < now - 60s`，单批上限 50。

存量迁移 CLI `scripts/migrate-files-to-kodo.py` 与同步中心共用 `storage_sync_service`。
"""

import asyncio
import importlib.util
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import settings
from app.models.file import (
    STORAGE_STATUS_FAILED,
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)
from app.services import storage
from app.services import storage_sync_service as svc

pytestmark = pytest.mark.fast

_seq = 0
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migrate-files-to-kodo.py"


def _next_seq() -> int:
    global _seq
    _seq += 1
    return _seq


# 辅助函数：将时间戳或 datetime 转换为带时区的 datetime
def _as_datetime(value: float | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    # int/float 时间戳
    return datetime.fromtimestamp(value, tz=timezone.utc)


@pytest.fixture(autouse=True)
def _storage_env(test_db, monkeypatch):
    """启用 memory 对象存储 + 清 storage.* 覆盖行 + 清后端缓存（用后复原）"""
    from app.models.system_config import SystemConfig

    def _clean():
        test_db.query(SystemConfig).filter(SystemConfig.key.like("storage.%")).delete()
        test_db.commit()
        storage.clear_backend_cache()

    _clean()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
    yield
    _clean()


def _backend(test_db):
    return storage.resolve_backend(storage.load_storage_config(test_db))


def _refetch(test_db, record_id: int) -> File | None:
    """工厂/CLI 内部会 `session.close()`（实例被 detach）→ 重新查询取新实例"""
    return test_db.query(File).filter(File.id == record_id).first()


def _insert_file(
    test_db,
    *,
    user_id: int = 1,
    status: int = STORAGE_STATUS_FAILED,
    created_at: float | datetime | None = None,
    write_disk: bool = True,
    deleted_at: float | datetime | None = None,
    storage_col: str = "memory",
) -> File:
    import hashlib
    import os

    seq = _next_seq()
    rel_path = f"comp-test/{user_id}/f-{seq}.jpg"
    if write_disk:
        abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(b"x" * 16)
    record = File(
        user_id=user_id,
        md5=hashlib.md5(f"comp-{seq}".encode()).hexdigest(),
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=16,
        mime_type="image/jpeg",
        upload_source="gear_image",
        ref_count=0,
        created_at=_as_datetime(created_at),
        storage=storage_col,
        storage_status=status,
        deleted_at=_as_datetime(deleted_at) if deleted_at is not None else None,
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


# ==================== 扫描条件（§5.3） ====================


class TestFindStale:
    def test_returns_timed_out_pending_and_failed(self, test_db):
        stale = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)
        pending = _insert_file(test_db, status=STORAGE_STATUS_PENDING, created_at=time.time() - 120)
        found = svc.find_stale(test_db)
        ids = {r.id for r in found}
        assert {stale.id, pending.id} <= ids

    def test_excludes_recent_and_synced_and_deleted(self, test_db):
        recent = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time())
        synced = _insert_file(test_db, status=STORAGE_STATUS_SYNCED, created_at=time.time() - 600)
        deleted = _insert_file(
            test_db,
            status=STORAGE_STATUS_FAILED,
            created_at=time.time() - 600,
            deleted_at=time.time() - 10,
        )
        ids = {r.id for r in svc.find_stale(test_db)}
        assert {recent.id, synced.id, deleted.id}.isdisjoint(ids)

    def test_user_filter_and_limit(self, test_db):
        for _ in range(3):
            _insert_file(
                test_db, user_id=7, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120
            )
        _insert_file(test_db, user_id=8, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)

        assert len(svc.find_stale(test_db, user_id=7)) == 3
        assert len(svc.find_stale(test_db, limit=2)) == 2


# ==================== 补偿执行 ====================


class TestCompensate:
    def test_stale_failed_is_compensated(self, test_db):
        rec = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)
        result = svc.compensate(test_db)

        assert result["queued"] >= 1
        assert result["failed"] == 0
        test_db.refresh(rec)
        assert rec.storage_status == STORAGE_STATUS_SYNCED
        assert _backend(test_db).head(rec.rel_path) is not None

    def test_grace_window_skips_fresh_records(self, test_db):
        rec = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time())
        result = svc.compensate(test_db)

        assert result["queued"] == 0
        test_db.refresh(rec)
        assert rec.storage_status == STORAGE_STATUS_FAILED

    def test_batch_limit_respected(self, test_db):
        for _ in range(3):
            _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)
        result = svc.compensate(test_db, limit=2)
        assert result["queued"] == 2

    def test_local_backend_is_noop(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
        storage.clear_backend_cache()
        _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)

        result = svc.compensate(test_db)
        assert result["disabled"] is True
        assert result["queued"] == 0

    def test_conflict_skips_when_sync_running(self, test_db):
        rec = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)
        svc.RUN_STATE.running = True
        try:
            result = svc.compensate(test_db)
        finally:
            svc.RUN_STATE.running = False

        assert result["conflict"] is True
        test_db.refresh(rec)
        assert rec.storage_status == STORAGE_STATUS_FAILED

    def test_single_failure_does_not_break_batch(self, test_db, monkeypatch):
        bad = _insert_file(
            test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120, write_disk=False
        )
        good = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)

        result = svc.compensate(test_db)

        assert result["queued"] == 2
        assert result["failed"] == 1
        test_db.refresh(bad)
        test_db.refresh(good)
        assert bad.storage_status == STORAGE_STATUS_FAILED
        assert good.storage_status == STORAGE_STATUS_SYNCED


# ==================== 触发点 1：启动 ====================


class TestStartupTrigger:
    def test_runs_compensation_with_injected_factory(self, test_db):
        rec = _insert_file(test_db, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)
        rec_id = rec.id
        result = svc.run_startup_compensation(session_factory=lambda: test_db)
        assert result is not None
        assert result["queued"] >= 1
        row = _refetch(test_db, rec_id)
        assert row is not None
        assert row.storage_status == STORAGE_STATUS_SYNCED

    def test_swallows_factory_errors(self):
        def _boom():
            raise RuntimeError("db down")

        assert svc.run_startup_compensation(session_factory=_boom) is None

    def test_schedule_without_loop_is_noop(self):
        assert svc.schedule_startup_compensation() is False

    def test_schedule_in_loop_executes_once(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            svc, "run_startup_compensation", lambda *a, **k: calls.append(k) or {"queued": 0}
        )

        async def _go():
            assert svc.schedule_startup_compensation() is True
            await asyncio.sleep(0.1)  # 等线程池任务完成

        asyncio.run(_go())
        assert len(calls) == 1


# ==================== 触发点 2：上传后顺带 ====================


class TestUploadTrigger:
    def test_compensates_same_user_only(self, test_db):
        mine = _insert_file(
            test_db, user_id=1, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120
        )
        other = _insert_file(
            test_db, user_id=2, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120
        )

        svc.compensate_after_upload(test_db, user_id=1)

        test_db.refresh(mine)
        test_db.refresh(other)
        assert mine.storage_status == STORAGE_STATUS_SYNCED
        assert other.storage_status == STORAGE_STATUS_FAILED

    def test_never_raises(self, test_db, monkeypatch):
        _insert_file(test_db, user_id=1, status=STORAGE_STATUS_FAILED, created_at=time.time() - 120)

        def _boom(*a, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(svc, "compensate", _boom)
        svc.compensate_after_upload(test_db, user_id=1)  # 不应抛出


# ==================== 存量迁移 CLI ====================


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("migrate_files_to_kodo", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigrateCli:
    def test_dry_run_counts_without_changes(self, test_db):
        rec = _insert_file(test_db, storage_col="local", status=STORAGE_STATUS_SYNCED)
        rec_id = rec.id
        cli = _load_cli_module()

        result = cli.run(
            cli.build_parser().parse_args(["--scope", "local", "--dry-run"]),
            session_factory=lambda: test_db,
        )

        assert result["exit_code"] == 0
        assert result["queued"] >= 1
        row = _refetch(test_db, rec_id)
        assert row is not None
        assert row.storage == "local"  # 零改动

    def test_scope_local_migrates(self, test_db):
        rec = _insert_file(test_db, storage_col="local", status=STORAGE_STATUS_PENDING)
        rec_id = rec.id
        cli = _load_cli_module()

        result = cli.run(
            cli.build_parser().parse_args(["--scope", "local"]),
            session_factory=lambda: test_db,
        )

        assert result["exit_code"] == 0
        row = _refetch(test_db, rec_id)
        assert row is not None
        assert row.storage == "memory"
        assert row.storage_status == STORAGE_STATUS_SYNCED

    def test_backend_local_exits_nonzero(self, test_db, monkeypatch, capsys):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
        storage.clear_backend_cache()
        cli = _load_cli_module()

        result = cli.run(
            cli.build_parser().parse_args(["--scope", "local"]),
            session_factory=lambda: test_db,
        )

        assert result["exit_code"] == 1
        assert "未启用对象存储" in capsys.readouterr().err

    def test_unknown_scope_exits_nonzero(self, test_db):
        cli = _load_cli_module()
        result = cli.run(
            cli.build_parser().parse_args(["--scope", "nope"]),
            session_factory=lambda: test_db,
        )
        assert result["exit_code"] == 1
