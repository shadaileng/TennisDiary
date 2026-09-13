"""管线异常状态兜底测试（139 Step 1，目标 G2 / G3）

覆盖：
- G3：`register_batch` 的 flush 失败后，不得把调用方的数据库会话留在
  pending-rollback 坏状态（否则后续所有写操作连带失败）
- G2：管线任何异常都必须把 `analyses.status` 落到 `failed`，且 `pipeline_status.error` 非空
- G2 兜底：即便管线自身会话 `self.db` 已损坏，也要通过**独立连接**兜底写入 `failed`

对应方案：`docs/plans/139-管线异常状态兜底与日志规范修正.md` §5.1 / §5.2
"""

import json

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.analysis import Analysis
from app.services import file_service
from app.services.pipeline import PipelineEngine

pytestmark = pytest.mark.fast


def _make_analysis(db, status: str = "processing") -> Analysis:
    """建一条分析记录并返回"""
    analysis = Analysis(
        user_id=1,
        date="2026-09-08",
        kind="正手",
        mode="single",
        status=status,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _draft(md5: str, name: str = "a.jpg") -> "file_service.FileDraft":
    return file_service.FileDraft(
        md5=md5,
        size=1,
        ext=".jpg",
        upload_source="video_frame",
        original_name=name,
    )


class TestRegisterBatchSessionSafety:
    """G3：批量登记失败不得污染调用方会话"""

    def test_flush_failure_triggers_rollback(self, test_db, monkeypatch):
        """flush 失败时必须 rollback，否则调用方会话会残留 pending-rollback 坏状态

        修复前：register_batch 的 `db.flush()`（file_service.py:391）无 try/rollback，
        失败后调用方会话进入坏状态，导致后续所有 DB 操作（含 status="failed"）连带失败。

        注：此处直接断言 `rollback` 被调用——若仅 mock 掉 flush 再验证"会话仍可用"，
        由于 SQLAlchemy 内部事务从未真正变坏，会产生假阳性。
        """
        rollback_calls = []
        original_rollback = test_db.rollback

        def boom(*_args, **_kwargs):
            raise RuntimeError("flush boom")

        def tracked_rollback(*_args, **_kwargs):
            rollback_calls.append(True)
            return original_rollback(*_args, **_kwargs)

        monkeypatch.setattr(test_db, "flush", boom)
        monkeypatch.setattr(test_db, "rollback", tracked_rollback)

        with pytest.raises(RuntimeError, match="flush boom"):
            file_service.register_batch(
                db=test_db,
                user_id=1,
                items=[_draft("a" * 32)],
            )

        assert rollback_calls, "flush 失败后必须 rollback，否则会污染调用方会话"

    def test_original_exception_is_preserved(self, test_db, monkeypatch):
        """register_batch 失败时原异常语义保留（仍抛出，交由调用方处理）"""

        def boom(*_args, **_kwargs):
            raise ValueError("原始异常应保持")

        monkeypatch.setattr(test_db, "flush", boom)

        with pytest.raises(ValueError, match="原始异常应保持"):
            file_service.register_batch(
                db=test_db,
                user_id=1,
                items=[_draft("b" * 32)],
            )


class TestPipelineFailureStatus:
    """G2：管线异常必须把状态落到 failed"""

    def test_pipeline_exception_sets_status_failed(self, test_db, monkeypatch):
        """步骤抛错 → status=failed 且 pipeline_status.error 非空"""
        analysis = _make_analysis(test_db)
        engine = PipelineEngine(test_db, analysis.id)
        engine.max_retries = 1  # 跳过指数退避，避免测试变慢

        def boom(*_args, **_kwargs):
            raise RuntimeError("步骤炸了")

        monkeypatch.setattr(PipelineEngine, "_process_video", boom)

        result = engine.run_pipeline("/nonexistent.mp4", {})

        assert result["status"] == "failed"

        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == analysis.id).first()
        assert got.status == "failed"

        pipeline_status = json.loads(got.pipeline_status or "{}")
        assert pipeline_status.get("error")

        # 失败原因须同步写入 summary：报告页展示依赖 summary
        # （Analysis 响应不含 pipeline_status，只写 error 会导致重新进入时看不到原因）
        assert got.summary

    def test_pipeline_sets_failed_even_when_session_broken(self, test_db, test_engine, monkeypatch):
        """即便 self.db 已不可写，独立连接兜底也要把状态置为 failed

        模拟 `self.db` 处于坏状态：所有 execute 均抛错，此时主路径的
        `_update_analysis_field(status="failed")` 必然失败，必须靠独立连接兜底。
        """
        analysis = _make_analysis(test_db)
        # 先缓存 id：后续 rollback 会 expire 该对象，而 test_db.execute 已被 mock 为不可用
        analysis_id = analysis.id

        # 独立连接工厂：与 test_db 同库，但每次新建 session
        factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

        engine = PipelineEngine(test_db, analysis_id, session_factory=factory)
        engine.max_retries = 1

        def boom(*_args, **_kwargs):
            raise RuntimeError("步骤炸了")

        monkeypatch.setattr(PipelineEngine, "_process_video", boom)

        def broken_execute(*_args, **_kwargs):
            raise RuntimeError("connection is broken")

        monkeypatch.setattr(test_db, "execute", broken_execute)

        result = engine.run_pipeline("/nonexistent.mp4", {})

        assert result["status"] == "failed"

        # 用全新 session 校验兜底写入生效
        verify = factory()
        try:
            got = verify.query(Analysis).filter(Analysis.id == analysis_id).first()
            assert got is not None
            assert got.status == "failed"
        finally:
            verify.close()

    def test_force_fail_does_not_raise(self, test_db, test_engine):
        """兜底写入自身失败时不得向外抛异常（避免二次抛出掩盖原始错误）"""
        from app.services.pipeline import _force_fail

        analysis = _make_analysis(test_db)
        factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

        # analysis_id 不存在时兜底应静默失败，不抛异常
        _force_fail(999999, "不存在的记录", factory)

        # 正常路径：写入成功
        _force_fail(analysis.id, "兜底失败原因", factory)

        verify = factory()
        try:
            got = verify.query(Analysis).filter(Analysis.id == analysis.id).first()
            assert got.status == "failed"
        finally:
            verify.close()
