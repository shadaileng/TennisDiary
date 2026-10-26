"""S3 同步中心（147 §9.1）：存量搬迁 / 失败补偿 / 状态核对

**单一服务源**：Admin 同步端点（`start_sync` / `sync_one`）、补偿任务（§5.3 三触发点）、
存量迁移 CLI（`scripts/migrate-files-to-kodo.py`，Step 10）共用本模块一套逻辑。

设计要点（§9.1 实现要点）：
- 幂等：`SYNCED` 默认跳过（天然断点续传）；`force=True` 对已 `SYNCED` 也重传（HEAD 核对）
- 批量：游标/条件筛选后逐条 `PUT` + 逐条落库，单条失败计数继续，不中断整批
- 防并发：进程内 `RUN_STATE.running` 标志（当前单 worker 部署）→ 进行中再触发 409
- 长任务走 `BackgroundTasks`（119 先例，**不引入常驻线程**，守 AGENTS 4.2）
- 进度：进程内计数，`sync-status` 读取；重启归零可接受（幂等可重跑）
- 边界：只上传不删本地（`storage.local_retention` 独立生效）；`backend=local` 抛
  `SyncDisabledError` → 端点 400（回滚档位下同步无意义）
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.models.file import (
    STORAGE_STATUS_FAILED,
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)
from app.services import file_service
from app.services.storage import load_storage_config
from app.services.storage.config import StorageConfig

log = get_logger("admin")

# 同步范围（§9.1 入参 scope）
SCOPES = ("pending", "failed", "local", "selected")


class SyncDisabledError(Exception):
    """未启用对象存储（storage.backend=local，回滚档位）"""


class SyncConflictError(Exception):
    """已有同步任务正在执行（进程内防并发）"""


class SyncValidationError(Exception):
    """同步入参非法（未知 scope / selected 缺 file_ids 等）"""


@dataclass
class SyncRunState:
    """进程内运行状态（单 worker；重启归零可接受，幂等可重跑）"""

    running: bool = False
    task_id: str = ""
    scope: str = ""
    done: int = 0
    total: int = 0
    failed: int = 0
    last_sync_at: float | None = None

    def snapshot(self) -> dict:
        return {
            "running": self.running,
            "task_id": self.task_id or None,
            "scope": self.scope or None,
            "progress": (
                {"done": self.done, "total": self.total, "failed": self.failed}
                if self.total
                else None
            ),
            "last_sync_at": self.last_sync_at,
        }


# 模块级运行状态（测试可直接改写 `RUN_STATE.running` 模拟执行中）
RUN_STATE = SyncRunState()
_RUN_LOCK = threading.Lock()


def _require_enabled(db: Session) -> StorageConfig:
    cfg = load_storage_config(db)
    if cfg.is_local:
        raise SyncDisabledError("未启用对象存储（storage.backend=local）")
    return cfg


def _acquire(scope: str, total: int) -> str:
    """抢占运行标志；已有任务在跑则 409"""
    with _RUN_LOCK:
        if RUN_STATE.running:
            raise SyncConflictError("已有同步任务正在执行，请稍后再试")
        task_id = uuid.uuid4().hex[:12]
        RUN_STATE.running = True
        RUN_STATE.task_id = task_id
        RUN_STATE.scope = scope
        RUN_STATE.done = 0
        RUN_STATE.total = total
        RUN_STATE.failed = 0
        return task_id


def _release() -> None:
    with _RUN_LOCK:
        RUN_STATE.running = False
        RUN_STATE.last_sync_at = time.time()


def sync_status(db: Session) -> dict:
    """同步中心统计（验收 #12：与 DB 实际一致）"""
    cfg = _require_enabled(db)
    rows = db.query(File.storage, File.storage_status).filter(File.deleted_at.is_(None)).all()
    with _RUN_LOCK:
        snapshot = RUN_STATE.snapshot()
    return {
        "total": len(rows),
        "synced": sum(1 for _, status in rows if status == STORAGE_STATUS_SYNCED),
        "pending": sum(1 for _, status in rows if status == STORAGE_STATUS_PENDING),
        "failed": sum(1 for _, status in rows if status == STORAGE_STATUS_FAILED),
        "local_only": sum(1 for storage_col, _ in rows if storage_col != cfg.backend),
        "running": snapshot["running"],
        "progress": snapshot["progress"],
        "last_sync_at": snapshot["last_sync_at"],
    }


def select_records(db: Session, cfg: StorageConfig, scope: str, file_ids=None) -> list[File]:
    """按 scope 筛选未软删记录"""
    query = db.query(File).filter(File.deleted_at.is_(None))
    if scope == "pending":
        query = query.filter(File.storage_status == STORAGE_STATUS_PENDING)
    elif scope == "failed":
        query = query.filter(File.storage_status == STORAGE_STATUS_FAILED)
    elif scope == "local":
        query = query.filter(File.storage != cfg.backend)
    elif scope == "selected":
        if not file_ids:
            raise SyncValidationError("scope=selected 需要 file_ids")
        query = query.filter(File.id.in_(list(file_ids)))
    else:
        raise SyncValidationError(f"未知同步范围: {scope}")
    return query.all()


def plan(
    db: Session, scope: str, file_ids=None, *, force: bool = False
) -> tuple[list[File], int, int]:
    """筛选 + 分拣：返回 (待同步记录, 跳过数, 待同步字节数)

    跳过口径：已 `SYNCED` 且位置即当前后端（且未 `force`）→ 幂等跳过。
    """
    cfg = _require_enabled(db)
    records = select_records(db, cfg, scope, file_ids)
    to_sync: list[File] = []
    skipped = 0
    estimate_bytes = 0
    for record in records:
        already_synced = (
            record.storage == cfg.backend and record.storage_status == STORAGE_STATUS_SYNCED
        )
        if already_synced and not force:
            skipped += 1
            continue
        to_sync.append(record)
        estimate_bytes += record.size_bytes or 0
    return to_sync, skipped, estimate_bytes


def _sync_records(db: Session, records: list[File], *, force: bool) -> tuple[int, int]:
    """逐条同步 + 逐条落库；单条失败计数继续，不中断整批（调用方需已 `_acquire`）"""
    synced = 0
    failed = 0
    for record in records:
        try:
            ok = file_service.sync_to_storage(db, record, force=force)
        except Exception as exc:
            db.rollback()
            log.exception("同步单条记录异常: {} {}", record.rel_path, exc)
            ok = False
        else:
            db.commit()
        with _RUN_LOCK:
            RUN_STATE.done += 1
            if ok:
                synced += 1
            else:
                RUN_STATE.failed += 1
                failed += 1
    return synced, failed


def start_sync(
    db: Session,
    *,
    scope: str,
    file_ids=None,
    dry_run: bool = False,
    force: bool = False,
    background: BackgroundTasks | None = None,
) -> dict:
    """HTTP 入口：dry_run 只统计；正式执行入队 `BackgroundTasks` 后立即返回

    Raises:
        SyncDisabledError: `backend=local`
        SyncConflictError: 已有任务在执行（409）
        SyncValidationError: 入参非法（400）
    """
    to_sync, skipped, estimate_bytes = plan(db, scope, file_ids, force=force)
    if dry_run:
        return {
            "dry_run": True,
            "scope": scope,
            "queued": len(to_sync),
            "skipped": skipped,
            "estimate_bytes": estimate_bytes,
            "task_id": None,
        }
    if not to_sync or background is None:
        # 无可同步项：直接返回（不占运行标志）
        return {
            "dry_run": False,
            "scope": scope,
            "queued": 0,
            "skipped": skipped,
            "estimate_bytes": 0,
            "task_id": None,
        }

    ids = [record.id for record in to_sync]
    task_id = _acquire(scope, len(ids))
    bind = db.get_bind()
    background.add_task(_run_in_background, bind, ids, force, task_id, scope)
    return {
        "dry_run": False,
        "scope": scope,
        "queued": len(ids),
        "skipped": skipped,
        "estimate_bytes": estimate_bytes,
        "task_id": task_id,
    }


def _run_in_background(bind, ids: list[int], force: bool, task_id: str, scope: str) -> None:
    """后台执行（请求会话已随响应关闭 → 用同一引擎新建会话，119 先例）"""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    db = factory()
    try:
        records = db.query(File).filter(File.id.in_(ids), File.deleted_at.is_(None)).all()
        synced, failed = _sync_records(db, records, force=force)
        log.info(
            "S3 同步任务完成: task_id={} scope={} synced={} failed={}",
            task_id,
            scope,
            synced,
            failed,
        )
    except Exception as exc:
        log.exception("S3 同步任务异常: {} {}", task_id, exc)
    finally:
        db.close()
        _release()


def run_sync(db: Session, scope: str, file_ids=None, *, force: bool = False) -> dict:
    """同步执行入口（CLI / 补偿任务用）：同步跑完再返回，行为与在线同步一致"""
    cfg = _require_enabled(db)
    records = select_records(db, cfg, scope, file_ids)
    task_id = _acquire(scope, len(records))
    try:
        to_sync = [
            r
            for r in records
            if force or not (r.storage == cfg.backend and r.storage_status == STORAGE_STATUS_SYNCED)
        ]
        synced, failed = _sync_records(db, to_sync, force=force)
    finally:
        _release()
    log.info("S3 同步完成: task_id={} scope={} synced={} failed={}", task_id, scope, synced, failed)
    return {"synced": synced, "failed": failed, "total": len(records)}


def sync_one(db: Session, file_id: int, *, force: bool = False) -> dict | None:
    """单条同步（表格行内按钮）；记录不存在/已软删返回 None（→ 404）"""
    _require_enabled(db)
    record = db.query(File).filter(File.id == file_id, File.deleted_at.is_(None)).first()
    if record is None:
        return None
    task_id = _acquire("single", 1)
    try:
        try:
            ok = file_service.sync_to_storage(db, record, force=force)
            db.commit()
        except Exception as exc:
            db.rollback()
            log.exception("单条同步异常: {} {}", record.rel_path, exc)
            ok = False
        with _RUN_LOCK:
            RUN_STATE.done = 1
            RUN_STATE.failed = 0 if ok else 1
    finally:
        _release()
    return {
        "file_id": record.id,
        "rel_path": record.rel_path,
        "status": "synced" if ok else "failed",
        "storage": record.storage,
        "storage_status": record.storage_status,
        "task_id": task_id,
    }


# ==================== 补偿任务（§5.3 三触发点） ====================
#
# 不引入常驻线程（AGENTS 4.2 禁后台自启服务），三个触发点共用 `compensate`：
# 1. 启动时：`schedule_startup_compensation`（lifespan）→ `run_startup_compensation`
# 2. 请求内顺带：上传成功后 `compensate_after_upload`（同用户、小批量、不外抛）
# 3. Admin 手动：`POST /files/sync scope=failed`（Step 8）

COMPENSATE_GRACE_SECONDS = 60  # 给正常上传留窗口
COMPENSATE_BATCH_LIMIT = 50  # 单批上限，防打爆
UPLOAD_COMPENSATE_LIMIT = 5  # 上传后顺带的批上限（请求内，必须轻）

# 启动补偿的一次性任务引用（防 GC；不是常驻任务）
_startup_task: asyncio.Task | None = None


def find_stale(
    db: Session,
    *,
    user_id: int | None = None,
    grace_seconds: float = COMPENSATE_GRACE_SECONDS,
    limit: int = COMPENSATE_BATCH_LIMIT,
) -> list[File]:
    """§5.3 扫描条件：`storage_status IN (0,2) AND created_at < now - 60s`（未软删）"""
    cutoff = time.time() - grace_seconds
    query = (
        db.query(File)
        .filter(
            File.storage_status.in_([STORAGE_STATUS_PENDING, STORAGE_STATUS_FAILED]),
            File.created_at < cutoff,
            File.deleted_at.is_(None),
        )
        .order_by(File.created_at.asc())
    )
    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    if limit:
        query = query.limit(limit)
    return query.all()


def compensate(
    db: Session,
    *,
    user_id: int | None = None,
    grace_seconds: float = COMPENSATE_GRACE_SECONDS,
    limit: int = COMPENSATE_BATCH_LIMIT,
    force: bool = False,
) -> dict:
    """补偿重传超时 `PENDING/FAILED` 记录（同步执行，幂等、单条失败不中断整批）

    Returns:
        统一结构 `{disabled, conflict, queued, synced, failed}`：
        - `disabled=True`：`backend=local`（回滚档位）→ 静默 no-op，不抛错
        - `conflict=True`：已有同步任务在执行 → 本次跳过（不与同步中心抢跑）
    """
    cfg = load_storage_config(db)
    if cfg.is_local:
        return {"disabled": True, "conflict": False, "queued": 0, "synced": 0, "failed": 0}

    records = find_stale(db, user_id=user_id, grace_seconds=grace_seconds, limit=limit)
    if not records:
        return {"disabled": False, "conflict": False, "queued": 0, "synced": 0, "failed": 0}

    try:
        task_id = _acquire("compensate", len(records))
    except SyncConflictError:
        log.info("补偿任务跳过：已有同步任务在执行（待补偿 {} 条）", len(records))
        return {"disabled": False, "conflict": True, "queued": 0, "synced": 0, "failed": 0}

    try:
        synced, failed = _sync_records(db, records, force=force)
    finally:
        _release()
    log.info(
        "补偿任务完成: task_id={} queued={} synced={} failed={}",
        task_id,
        len(records),
        synced,
        failed,
    )
    return {
        "disabled": False,
        "conflict": False,
        "queued": len(records),
        "synced": synced,
        "failed": failed,
    }


def compensate_after_upload(
    db: Session,
    *,
    user_id: int,
    grace_seconds: float = COMPENSATE_GRACE_SECONDS,
) -> dict | None:
    """触发点 2：上传成功后顺带重传**同用户**超时 `FAILED`（低频、无感）

    任何异常只记日志绝不外抛 —— 补偿失败绝不能影响上传主流程。
    """
    try:
        return compensate(
            db, user_id=user_id, grace_seconds=grace_seconds, limit=UPLOAD_COMPENSATE_LIMIT
        )
    except Exception as exc:  # noqa: BLE001 - 补偿任何异常都不能外抛
        log.warning("上传后补偿任务失败: user_id={} {}", user_id, exc)
        return None


def run_startup_compensation(session_factory=None) -> dict | None:
    """触发点 1：启动时扫一次超时记录（一次性，非常驻线程；异常只记日志）

    Args:
        session_factory: 会话工厂（测试注入）；缺省用 `SessionLocal`
    """
    try:
        factory = session_factory
        if factory is None:
            from app.core.database import SessionLocal

            factory = SessionLocal
        db = factory()
        try:
            return compensate(db)
        finally:
            db.close()
    except Exception as exc:
        log.exception("启动补偿任务失败: {}", exc)
        return None


def schedule_startup_compensation() -> bool:
    """lifespan 内调用：把启动补偿丢到线程池**一次性**执行（不阻塞启动）

    Returns:
        是否成功入队；无事件循环（同步上下文 / 测试）时跳过返回 `False`
    """
    global _startup_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    _startup_task = loop.create_task(asyncio.to_thread(run_startup_compensation))
    return True


__all__ = [
    "COMPENSATE_BATCH_LIMIT",
    "COMPENSATE_GRACE_SECONDS",
    "RUN_STATE",
    "SCOPES",
    "SyncConflictError",
    "SyncDisabledError",
    "SyncValidationError",
    "compensate",
    "compensate_after_upload",
    "find_stale",
    "plan",
    "run_startup_compensation",
    "run_sync",
    "schedule_startup_compensation",
    "select_records",
    "start_sync",
    "sync_one",
    "sync_status",
]
