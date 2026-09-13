"""孤儿 processing 分析记录清理测试（139 Step 8，目标 G4）

管线异常中断后若 `status="failed"` 也写不进去，记录会永久停留在 processing，
导致小程序端无限轮询。本模块提供**超时兜底**清理。

覆盖：
- 超时记录被置 failed 且写入错误原因
- 未超时记录不受影响
- 幂等：重复调用不重复处理
- `created_at` 为 0（历史脏数据）的记录不误伤
- 惰性触发的节流生效
"""

import json
import time

import pytest

from app.models.analysis import Analysis
from app.services.analysis_cleanup import (
    DEFAULT_TIMEOUT_S,
    cleanup_stuck_processing,
    maybe_cleanup_stuck_processing,
)

pytestmark = pytest.mark.fast

ERROR_TEXT = "分析超时，已自动置为失败"


def _make(
    db,
    status: str = "processing",
    created_at: float | None = None,
    pipeline_status: str | None = None,
) -> Analysis:
    analysis = Analysis(
        user_id=1,
        date="2026-09-08",
        kind="正手",
        mode="single",
        status=status,
        created_at=time.time() if created_at is None else created_at,
        pipeline_status=pipeline_status,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


class TestCleanupStuckProcessing:
    """超时兜底清理"""

    def test_timeout_record_marked_failed(self, test_db):
        """超过阈值的 processing 记录被置 failed 并写入错误原因"""
        now = time.time()
        stale = _make(test_db, created_at=now - (DEFAULT_TIMEOUT_S + 60))

        count = cleanup_stuck_processing(test_db, now=now)

        assert count == 1

        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == stale.id).first()
        assert got.status == "failed"

        pipeline_status = json.loads(got.pipeline_status or "{}")
        assert pipeline_status.get("error") == ERROR_TEXT

    def test_recent_record_untouched(self, test_db):
        """未超时的 processing 记录保持原状"""
        now = time.time()
        fresh = _make(test_db, created_at=now - 10)

        count = cleanup_stuck_processing(test_db, now=now)

        assert count == 0
        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == fresh.id).first()
        assert got.status == "processing"

    def test_completed_and_failed_untouched(self, test_db):
        """已完成/已失败的记录不受影响（哪怕很旧）"""
        now = time.time()
        done = _make(test_db, status="completed", created_at=now - 99999)
        failed = _make(test_db, status="failed", created_at=now - 99999)

        count = cleanup_stuck_processing(test_db, now=now)

        assert count == 0
        test_db.expire_all()
        assert test_db.query(Analysis).filter(Analysis.id == done.id).first().status == "completed"
        assert test_db.query(Analysis).filter(Analysis.id == failed.id).first().status == "failed"

    def test_zero_created_at_not_touched(self, test_db):
        """created_at 为 0 的历史脏数据不误伤（避免把正常记录误置 failed）"""
        now = time.time()
        legacy = _make(test_db, created_at=0)

        count = cleanup_stuck_processing(test_db, now=now)

        assert count == 0
        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == legacy.id).first()
        assert got.status == "processing"

    def test_idempotent(self, test_db):
        """重复调用幂等：第二次不再处理已置 failed 的记录"""
        now = time.time()
        _make(test_db, created_at=now - (DEFAULT_TIMEOUT_S + 60))

        assert cleanup_stuck_processing(test_db, now=now) == 1
        assert cleanup_stuck_processing(test_db, now=now) == 0

    def test_custom_timeout(self, test_db):
        """支持自定义阈值"""
        now = time.time()
        _make(test_db, created_at=now - 30)

        assert cleanup_stuck_processing(test_db, timeout_s=10, now=now) == 1


class TestMaybeCleanupThrottle:
    """惰性触发的节流"""

    def test_throttle_skips_within_window(self, test_db):
        """节流窗口内重复调用直接跳过"""
        now = time.time()
        _make(test_db, created_at=now - (DEFAULT_TIMEOUT_S + 60))

        first = maybe_cleanup_stuck_processing(test_db, force=True)
        # 紧接着的调用被节流跳过（返回 0）
        second = maybe_cleanup_stuck_processing(test_db)

        assert first == 1
        assert second == 0

    def test_force_bypasses_throttle(self, test_db):
        """force=True 强制执行"""
        now = time.time()
        _make(test_db, created_at=now - (DEFAULT_TIMEOUT_S + 60))

        assert maybe_cleanup_stuck_processing(test_db, force=True) == 1
        # 再造一条，force 仍可执行
        _make(test_db, created_at=now - (DEFAULT_TIMEOUT_S + 60))
        assert maybe_cleanup_stuck_processing(test_db, force=True) == 1
