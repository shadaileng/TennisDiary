"""管线引擎：编排电子教练分析流程（init → upload → ai ∥ pose → finalize）"""

import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

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


class PipelineEngine:
    """管线引擎：编排分析流程"""

    def __init__(self, db: Session, analysis_id: int):
        self.db = db
        self.analysis_id = analysis_id
        self.max_retries = 3
        self.retry_delay_base = 2  # 指数退避基数

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
        # 查询当前状态
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        if analysis is None:
            return

        pipeline_status = _parse_pipeline_status(analysis.pipeline_status)
        if pipeline_status is None:
            pipeline_status = _initial_pipeline_status()

        # 更新步骤
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

    def run_pipeline(self, video_path: str, metadata: dict) -> dict:
        """执行完整管线"""
        log.info("管线开始", analysis_id=self.analysis_id)

        try:
            # Step 1: 上传+抽帧
            video_result = self._run_step_with_retry(
                PipelineStep.UPLOAD, self._process_video, video_path, metadata
            )

            # Step 2+3: 并行执行 AI + 姿态
            frame_urls = video_result["frame_urls"]

            with ThreadPoolExecutor(max_workers=2) as executor:
                ai_future = executor.submit(
                    self._run_step_with_retry,
                    PipelineStep.AI,
                    self._analyze_ai,
                    frame_urls,
                    metadata,
                )
                pose_future = executor.submit(
                    self._run_step_with_retry,
                    PipelineStep.POSE,
                    self._analyze_pose,
                    frame_urls,
                    video_result,
                    metadata,
                )

                ai_result = ai_future.result()
                pose_result = pose_future.result()

            # Step 4: 收尾
            self._finalize()

            log.info("管线完成", analysis_id=self.analysis_id)
            return {"status": "completed", "ai": ai_result, "pose": pose_result}

        except Exception as e:  # noqa: BLE001 - 管线需要捕获所有异常
            tb = traceback.format_exc()
            log.error(
                f"管线失败 analysis_id={self.analysis_id} "
                f"error={type(e).__name__}: {str(e)[:200]}\n{tb}"
            )
            self._update_step_status(PipelineStep.FINALIZE, StepStatus.FAILED, error=str(e))
            # 更新 Analysis 状态为 failed
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
                    f"管线步骤失败 step={step.value} attempt={attempt + 1}/{self.max_retries} "
                    f"error={type(e).__name__}: {str(e)[:200]}"
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

    def _process_video(self, video_path: str, metadata: dict) -> dict:
        """视频处理（同步）"""
        from app.services import file_service, video_service

        mode = metadata.get("mode", "single")
        hit_time = metadata.get("hit_time")
        cuts = metadata.get("cuts")

        # 调用 video_service.process_video
        result = video_service.process_video(video_path, mode, hit_time, cuts)

        log.info(
            f"管线-视频处理完成: duration={result.get('duration', 0):.2f}s "
            f"frames={len(result.get('frame_urls', []))} "
            f"trimmed={result.get('trimmed', False)}"
        )

        # 文件登记由上传路由统一处理（get_or_create_file），此处仅更新 video_url
        if self.analysis_id:
            working_path = result.get("working_path")
            rel_video_url = file_service.abs_path_to_rel(working_path) if working_path else None
            self._update_analysis_field(video_url=rel_video_url)

        return result

    def _analyze_ai(self, frame_urls: list[str], metadata: dict) -> dict:
        """AI 评分（同步包装 async）"""
        import asyncio

        from app.services import ai_service
        from app.services.config_service import get_ai_config

        async def _run():
            return await ai_service.analyze_swing(
                frames=None,
                kind=metadata.get("kind", ""),
                mode=metadata.get("mode", "single"),
                ai_config=get_ai_config(self.db),
                frame_urls=frame_urls,
            )

        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(_run())
        finally:
            loop.close()

        # 落库
        if self.analysis_id and report:
            self._update_analysis_field(
                report=json.dumps(report, ensure_ascii=False),
                score=report.get("score", 0),
                ntrp=report.get("ntrp"),
                summary=report.get("summary", ""),
            )

        return report

    def _analyze_pose(self, frame_urls: list[str], video_result: dict, metadata: dict) -> dict:
        """姿态推理（同步）"""
        from app.services import file_service, pose_service

        save_skeleton = True
        duration = video_result.get("duration")
        frame_rate = video_result.get("frame_rate")
        # process_video 返回 working_path（绝对路径），pose_service 需要相对路径
        working_path = video_result.get("working_path")
        video_url = file_service.abs_path_to_rel(working_path) if working_path else None

        # 调用 pose_service.analyze_frames
        result = pose_service.analyze_frames(
            frames=None,
            video_url=video_url,
            save_skeleton=save_skeleton,
            duration=duration,
            frame_rate=frame_rate,
            frame_urls=frame_urls,
        )

        # 登记骨架文件（使用 get_or_create_file 统一处理，支持秒传去重）
        if self.analysis_id and result:
            skeleton_frames = result.get("skeleton_frames") or []
            skeleton_video = result.get("skeleton_video_url")
            skeleton_thumb = result.get("skeleton_thumb")

            # 骨架帧（每帧用 savepoint 隔离，单帧失败不影响其余）
            for frame_path in skeleton_frames:
                try:
                    with self.db.begin_nested():
                        abs_p = file_service.rel_path_to_abs(frame_path)
                        file_service.get_or_create_file(
                            db=self.db,
                            user_id=self._get_user_id(),
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
                            user_id=self._get_user_id(),
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
                            user_id=self._get_user_id(),
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
            self._update_analysis_field(
                pose=json.dumps(result, ensure_ascii=False),
                thumb=skeleton_thumb,
            )

        return result

    def _finalize(self) -> None:
        """收尾更新状态"""
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        if analysis and analysis.video_url:
            self._update_analysis_field(status="completed")
            # 更新管线状态
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

    def _get_user_id(self) -> int:
        """获取分析记录的用户 ID"""
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        return analysis.user_id if analysis else 0


def _parse_pipeline_status(raw: str | None) -> dict | None:
    """解析 pipeline_status JSON"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None
