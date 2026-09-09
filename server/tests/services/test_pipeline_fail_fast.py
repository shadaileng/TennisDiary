"""管线步骤异常 fail-fast 测试（139 Step 4，目标 G5）

覆盖：
- 抽帧登记失败 → 管线终止，不得带着空输入静默进入 AI/pose（原"假成功"路径）
- 登记"成功"但 frame_urls 为空 → 0 帧硬校验触发失败
- `_finalize` 遇 `video_url` 为空 → 置 `failed`，不再保留 processing 孤儿（原"假处理中"路径）
- 可降级项（骨架登记）失败 → 管线仍完成，但写入 `pipeline_status.degraded` 打标

对应方案：`docs/plans/139-管线异常状态兜底与日志规范修正.md` §5.4
"""

import json

import pytest

from app.models.analysis import Analysis
from app.services.pipeline import PipelineEngine, PipelineStep

pytestmark = pytest.mark.fast


def _make_analysis(db, status: str = "processing", video_url: str | None = None) -> Analysis:
    analysis = Analysis(
        user_id=1,
        date="2026-09-08",
        kind="正手",
        mode="single",
        status=status,
        video_url=video_url,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


class TestFailFast:
    """G5：致命步骤失败必须终止管线"""

    def test_frame_registration_failure_aborts_pipeline(self, test_db, monkeypatch):
        """抽帧登记抛错 → 管线终止并置 failed，不得继续 AI/pose

        修复前：异常被吞、置 `frame_urls = []`，UPLOAD 判定"成功"，
        AI/pose 拿 0 帧空跑，最终产出"已完成"的垃圾报告（§2.5 路径 A）。

        注：只 mock `video_service.process_video` 与 `file_service.register_batch`，
        保留真实的 `_process_video`，以验证其中的 fail-fast 逻辑。
        """
        from app.services import file_service, video_service

        analysis = _make_analysis(test_db)
        engine = PipelineEngine(test_db, analysis.id)
        engine.max_retries = 1

        ai_called = []

        # 视频处理成功，产出帧路径
        monkeypatch.setattr(
            video_service,
            "process_video",
            lambda *_a, **_k: {
                "frame_paths": ["/tmp/f0.jpg", "/tmp/f1.jpg"],
                "working_path": "/tmp/x.mp4",
                "trimmed": False,
            },
        )

        # 抽帧登记失败（致命）
        def boom(*_a, **_k):
            raise RuntimeError("抽帧登记炸了")

        monkeypatch.setattr(file_service, "register_batch", boom)

        def fake_ai(*_a, **_k):
            ai_called.append(True)
            return {"score": 0}

        monkeypatch.setattr(PipelineEngine, "_compute_ai", fake_ai)

        result = engine.run_pipeline("/fake.mp4", {})

        # 关键：管线失败，且 AI 从未被调用（不得带着空输入继续）
        assert result["status"] == "failed"
        assert not ai_called, "抽帧失败后不得继续进入 AI 步骤"

        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == analysis.id).first()
        assert got.status == "failed"

    def test_zero_frames_aborts_pipeline(self, test_db, monkeypatch):
        """抽帧结果为空 → 0 帧硬校验必须触发失败（登记"成功"也不可放行）"""
        from app.services import video_service

        analysis = _make_analysis(test_db)
        engine = PipelineEngine(test_db, analysis.id)
        engine.max_retries = 1

        # 抽帧结果为空：frame_paths 为空 → 登记返回空 → 触发硬校验
        monkeypatch.setattr(
            video_service,
            "process_video",
            lambda *_a, **_k: {
                "frame_paths": [],
                "working_path": "/tmp/x.mp4",
                "trimmed": False,
            },
        )

        result = engine.run_pipeline("/fake.mp4", {})

        assert result["status"] == "failed"
        assert "0 帧" in result["error"] or "抽帧" in result["error"]

    def test_empty_video_url_marks_failed(self, test_db):
        """`_finalize` 遇 video_url 为空 → 置 failed，不保留 processing 孤儿

        修复前：仅 `log.warning("…保留 processing 孤儿")`，状态永远停在
        processing，前端无限轮询（§2.5 路径 B）。
        """
        analysis = _make_analysis(test_db, status="processing", video_url=None)

        engine = PipelineEngine(test_db, analysis.id)
        engine._finalize()

        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == analysis.id).first()
        assert got.status == "failed", "video_url 为空必须置 failed，不得保留孤儿"

        pipeline_status = json.loads(got.pipeline_status or "{}")
        assert pipeline_status["steps"][PipelineStep.FINALIZE.value]["status"] == "failed"
        # 须写入可读的失败原因，供报告页展示
        assert got.summary == "播放短片缺失，分析未完成"

    def test_degraded_item_is_recorded(self, test_db):
        """可降级项失败 → 管线仍完成，但写入 pipeline_status.degraded 打标

        可降级项由调用方（如 `_write_pose_result`）通过 `_mark_degraded` 登记，
        `_finalize` 收尾时须保留该标记，不得覆盖丢失。
        """
        analysis = _make_analysis(test_db, video_url="videos/1/abc.mp4")
        engine = PipelineEngine(test_db, analysis.id)

        # 模拟可降级项（骨架文件登记）失败
        engine._mark_degraded("skeleton_files", "骨架文件登记失败")

        engine._finalize()

        test_db.expire_all()
        got = test_db.query(Analysis).filter(Analysis.id == analysis.id).first()
        # video_url 非空 → 正常完成
        assert got.status == "completed"

        pipeline_status = json.loads(got.pipeline_status or "{}")
        degraded = pipeline_status.get("degraded") or []
        assert any(item["item"] == "skeleton_files" for item in degraded)
