"""管线引擎：编排电子教练分析流程（init → upload → ai ∥ pose → finalize）

架构：计算并行 + 写表串行
- AI 与姿态检测在 ThreadPoolExecutor 并行执行（纯计算，无 DB 操作）
- DB 写入（score/summary/pose/骨架文件登记）在主线程串行完成，共用 self.db
- 仅线程内操作（如读取 AI 配置）使用独立 Session
"""

import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.analysis import Analysis

log = get_logger("pipeline")


class PipelineStep(str, Enum):
    """管线步骤"""

    INIT = "init"
    UPLOAD = "upload"
    AI = "ai"
    POSE = "pose"
    FINALIZE = "finalize"


class StepStatus(str, Enum):
    """步骤状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# 步骤默认进度
_STEP_PROGRESS = {
    PipelineStep.INIT: 0,
    PipelineStep.UPLOAD: 15,
    PipelineStep.AI: 50,
    PipelineStep.POSE: 50,
    PipelineStep.FINALIZE: 95,
}


def _initial_pipeline_status() -> dict:
    """初始化管线状态"""
    return {
        "step": PipelineStep.INIT.value,
        "progress": 0,
        "steps": {step.value: {"status": StepStatus.PENDING.value} for step in PipelineStep},
        "error": None,
        "retry_count": 0,
    }


def _parse_pipeline_status(raw: str | None) -> dict | None:
    """解析 pipeline_status JSON"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


class PipelineEngine:
    """管线引擎：编排分析流程

    架构：计算并行 + 写表串行
    - _compute_* 方法在 ThreadPoolExecutor 线程中执行（纯计算，无 DB 操作）
    - _write_* / _update_* 方法在主线程中执行，共用 self.db
    """

    def __init__(self, db: Session, analysis_id: int):
        self.db = db
        self.analysis_id = analysis_id
        self.max_retries = 3
        self.retry_delay_base = 2  # 指数退避基数

    # ==================== DB 操作（主线程，共用 self.db） ====================

    def _update_pipeline_status(self, status: dict) -> None:
        """列定向更新 pipeline_status"""
        stmt = (
            sa_update(Analysis)
            .where(Analysis.id == self.analysis_id)
            .values(pipeline_status=json.dumps(status, ensure_ascii=False))
        )
        self.db.execute(stmt)
        self.db.commit()

    def _update_analysis_field(self, **kwargs) -> None:
        """列定向更新 Analysis 字段"""
        stmt = sa_update(Analysis).where(Analysis.id == self.analysis_id).values(**kwargs)
        self.db.execute(stmt)
        self.db.commit()

    def _update_step_status(
        self,
        step: PipelineStep,
        status: StepStatus,
        progress: int | None = None,
        error: str | None = None,
    ) -> None:
        """更新步骤状态"""
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        if analysis is None:
            return

        pipeline_status = _parse_pipeline_status(analysis.pipeline_status)
        if pipeline_status is None:
            pipeline_status = _initial_pipeline_status()

        pipeline_status["step"] = step.value
        default_progress = _STEP_PROGRESS.get(step, 0)
        pipeline_status["progress"] = progress if progress is not None else default_progress
        pipeline_status["steps"][step.value] = {
            "status": status.value,
            "ts": time.time(),
        }
        if error:
            pipeline_status["error"] = error

        self._update_pipeline_status(pipeline_status)

    def _get_user_id(self) -> int:
        """获取分析记录的用户 ID"""
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        return analysis.user_id if analysis else 0

    # ==================== 管线主流程 ====================

    def run_pipeline(self, video_path: str, metadata: dict) -> dict:
        """执行完整管线：计算并行 + 写表串行"""
        log.info("管线开始", analysis_id=self.analysis_id)

        try:
            # Step 1: 上传+抽帧
            video_result = self._run_step_with_retry(
                PipelineStep.UPLOAD, self._process_video, video_path, metadata
            )

            # Step 2+3: 并行计算（纯计算，无 DB 操作）
            frame_urls = video_result["frame_urls"]

            with ThreadPoolExecutor(max_workers=2) as executor:
                ai_future = executor.submit(self._compute_ai, frame_urls, metadata)
                pose_future = executor.submit(
                    self._compute_pose, frame_urls, video_result, metadata
                )

                # 收集两个 future 的结果/异常，避免丢失任一方错误
                ai_result, ai_exc = None, None
                pose_result, pose_exc = None, None
                try:
                    ai_result = ai_future.result()
                except Exception as exc:  # noqa: BLE001
                    ai_exc = exc
                try:
                    pose_result = pose_future.result()
                except Exception as exc:  # noqa: BLE001
                    pose_exc = exc

                if ai_exc or pose_exc:
                    parts = []
                    if ai_exc:
                        parts.append(f"AI: {type(ai_exc).__name__}: {str(ai_exc)[:120]}")
                    if pose_exc:
                        parts.append(f"Pose: {type(pose_exc).__name__}: {str(pose_exc)[:120]}")
                    raise RuntimeError("; ".join(parts)) from (ai_exc or pose_exc)

            # Step 2+3 写表：串行执行（共用 self.db）
            self._update_step_status(PipelineStep.AI, StepStatus.PROCESSING)
            self._write_ai_result(ai_result)
            self._update_step_status(PipelineStep.AI, StepStatus.COMPLETED, progress=100)

            self._update_step_status(PipelineStep.POSE, StepStatus.PROCESSING)
            self._write_pose_result(pose_result)
            self._update_step_status(PipelineStep.POSE, StepStatus.COMPLETED, progress=100)

            # Step 4: 收尾
            self._finalize()

            log.info("管线完成", analysis_id=self.analysis_id)
            return {"status": "completed", "ai": ai_result, "pose": pose_result}

        except Exception as e:  # noqa: BLE001 - 管线需要捕获所有异常
            tb = traceback.format_exc()
            log.error(
                "管线失败 analysis_id=%s error=%s: %s\n%s",
                self.analysis_id,
                type(e).__name__,
                str(e)[:200],
                tb,
            )
            self._update_step_status(PipelineStep.FINALIZE, StepStatus.FAILED, error=str(e))
            self._update_analysis_field(status="failed")
            return {"status": "failed", "error": str(e)}

    def _run_step_with_retry(self, step: PipelineStep, func, *args, **kwargs):
        """执行单个步骤，支持重试"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._update_step_status(step, StepStatus.PROCESSING)
                result = func(*args, **kwargs)
                self._update_step_status(step, StepStatus.COMPLETED, progress=100)
                return result
            except Exception as e:  # noqa: BLE001 - 重试需要捕获所有异常
                last_error = e
                log.warning(
                    "管线步骤失败 step=%s attempt=%d/%d error=%s: %s",
                    step.value,
                    attempt + 1,
                    self.max_retries,
                    type(e).__name__,
                    str(e)[:200],
                )
                if attempt < self.max_retries - 1:
                    import time as _time

                    delay = self.retry_delay_base**attempt
                    _time.sleep(delay)
                    # 更新重试次数
                    analysis = (
                        self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
                    )
                    if analysis:
                        pipeline_status = _parse_pipeline_status(analysis.pipeline_status)
                        if pipeline_status:
                            pipeline_status["retry_count"] = attempt + 1
                            self._update_pipeline_status(pipeline_status)

        # 所有重试失败
        self._update_step_status(step, StepStatus.FAILED, error=str(last_error))
        raise last_error

    # ==================== 计算阶段（线程并行，无 DB 操作） ====================

    def _process_video(self, video_path: str, metadata: dict) -> dict:
        """视频处理（同步）"""
        from app.services import file_service, video_service

        mode = metadata.get("mode", "single")
        hit_time = metadata.get("hit_time")
        cuts = metadata.get("cuts")

        result = video_service.process_video(video_path, mode, hit_time, cuts)

        log.info(
            "管线-视频处理完成: duration=%.2fs frames=%d trimmed=%s",
            result.get("duration", 0),
            len(result.get("frame_urls", [])),
            result.get("trimmed", False),
        )

        # 文件登记由上传路由统一处理（get_or_create_file），此处仅更新 video_url
        if self.analysis_id:
            working_path = result.get("working_path")
            rel_video_url = file_service.abs_path_to_rel(working_path) if working_path else None
            self._update_analysis_field(video_url=rel_video_url)

        return result

    def _compute_ai(self, frame_urls: list[str], metadata: dict) -> dict:
        """AI 评分（线程内执行，用独立会话读配置）"""
        import asyncio

        from app.services import ai_service
        from app.services.config_service import get_ai_config

        # 线程内必须用独立 Session（self.db 不跨线程）
        db = SessionLocal()
        try:
            ai_config = get_ai_config(db)
        finally:
            db.close()

        async def _run():
            return await ai_service.analyze_swing(
                frames=None,
                kind=metadata.get("kind", ""),
                mode=metadata.get("mode", "single"),
                ai_config=ai_config,
                frame_urls=frame_urls,
            )

        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(_run())
        finally:
            loop.close()

        return report

    def _compute_pose(self, frame_urls: list[str], video_result: dict, metadata: dict) -> dict:
        """姿态推理（线程内执行，纯计算无 DB）"""
        from app.services import file_service, pose_service

        save_skeleton = True
        duration = video_result.get("duration")
        frame_rate = video_result.get("frame_rate")
        working_path = video_result.get("working_path")
        video_url = file_service.abs_path_to_rel(working_path) if working_path else None

        result = pose_service.analyze_frames(
            frames=None,
            video_url=video_url,
            save_skeleton=save_skeleton,
            duration=duration,
            frame_rate=frame_rate,
            frame_urls=frame_urls,
        )

        return result

    # ==================== 写表阶段（主线程串行，共用 self.db） ====================

    def _write_ai_result(self, ai_result: dict) -> None:
        """写入 AI 结果到数据库"""
        if self.analysis_id and ai_result:
            self._update_analysis_field(
                report=json.dumps(ai_result, ensure_ascii=False),
                score=ai_result.get("score", 0),
                ntrp=ai_result.get("ntrp"),
                summary=ai_result.get("summary", ""),
            )

    def _write_pose_result(self, pose_result: dict) -> None:
        """写入姿态结果到数据库（骨架文件登记 + Analysis 更新）"""
        if not (self.analysis_id and pose_result):
            return

        from app.services import file_service

        skeleton_frames = pose_result.get("skeleton_frames") or []
        skeleton_video = pose_result.get("skeleton_video_url")
        skeleton_thumb = pose_result.get("skeleton_thumb")
        user_id = self._get_user_id()

        # 骨架帧（每帧用 savepoint 隔离，单帧失败不影响其余）
        for frame_path in skeleton_frames:
            try:
                with self.db.begin_nested():
                    abs_p = file_service.rel_path_to_abs(frame_path)
                    file_service.get_or_create_file(
                        db=self.db,
                        user_id=user_id,
                        rel_path=frame_path,
                        abs_path=abs_p,
                        upload_source="skeleton_frame",
                        original_name=os.path.basename(frame_path),
                        business_type="analysis",
                        business_id=self.analysis_id,
                    )
            except Exception as exc:  # noqa: BLE001 - 单帧登记失败非致命
                log.warning(
                    "骨架帧登记失败(非致命): %s - %s",
                    type(exc).__name__,
                    str(exc)[:120],
                )

        # 骨架视频
        if skeleton_video:
            try:
                with self.db.begin_nested():
                    abs_p = file_service.rel_path_to_abs(skeleton_video)
                    file_service.get_or_create_file(
                        db=self.db,
                        user_id=user_id,
                        rel_path=skeleton_video,
                        abs_path=abs_p,
                        upload_source="skeleton_video",
                        original_name=os.path.basename(skeleton_video),
                        business_type="analysis",
                        business_id=self.analysis_id,
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "骨架视频登记失败(非致命): %s - %s",
                    type(exc).__name__,
                    str(exc)[:120],
                )

        # 骨架封面
        if skeleton_thumb:
            try:
                with self.db.begin_nested():
                    abs_p = file_service.rel_path_to_abs(skeleton_thumb)
                    file_service.get_or_create_file(
                        db=self.db,
                        user_id=user_id,
                        rel_path=skeleton_thumb,
                        abs_path=abs_p,
                        upload_source="skeleton_thumb",
                        original_name=os.path.basename(skeleton_thumb),
                        business_type="analysis",
                        business_id=self.analysis_id,
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "骨架封面登记失败(非致命): %s - %s",
                    type(exc).__name__,
                    str(exc)[:120],
                )

        self.db.commit()

        # 更新 Analysis.pose, thumb
        stmt = (
            sa_update(Analysis)
            .where(Analysis.id == self.analysis_id)
            .values(
                pose=json.dumps(pose_result, ensure_ascii=False),
                thumb=skeleton_thumb,
            )
        )
        self.db.execute(stmt)
        self.db.commit()

    def _finalize(self) -> None:
        """收尾更新状态"""
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        if analysis and analysis.video_url:
            self._update_analysis_field(status="completed")
            pipeline_status = _parse_pipeline_status(analysis.pipeline_status)
            if pipeline_status:
                pipeline_status["step"] = PipelineStep.FINALIZE.value
                pipeline_status["progress"] = 100
                pipeline_status["steps"][PipelineStep.FINALIZE.value] = {
                    "status": StepStatus.COMPLETED.value,
                    "ts": time.time(),
                }
                self._update_pipeline_status(pipeline_status)
        else:
            log.warning(
                "分析记录 video_url 为空，保留 processing 孤儿",
                analysis_id=self.analysis_id,
            )
