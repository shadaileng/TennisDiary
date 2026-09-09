"""管线引擎：编排电子教练分析流程（init → upload → ai ∥ pose → finalize）

架构：计算并行 + 写表串行
- AI 与姿态检测在 ThreadPoolExecutor 并行执行（纯计算，无 DB 操作）
- DB 写入（score/summary/pose/骨架文件登记）在主线程串行完成，共用 self.db
"""

import json
import os
import time
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
        "started_at": time.time(),
        "completed_at": None,
        "total_duration_s": None,
        "parallel_duration_s": None,
    }


def _parse_pipeline_status(raw: str | None) -> dict | None:
    """解析 pipeline_status JSON"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _force_fail(analysis_id: int, error: str, session_factory=None) -> None:
    """独立连接兜底置 failed：不依赖管线可能已损坏的 self.db

    139：管线自身的 db 在 flush/写入失败后会进入 pending-rollback 坏状态，
    此时 `self.db` 上的任何写入（含 status="failed"）都会失败。本函数用
    **全新连接**完成兜底写入，确保异常中断时状态必定落到 failed（G2）。

    Args:
        analysis_id: 分析记录 ID
        error: 失败原因
        session_factory: 会话工厂，默认 `SessionLocal`（生产）；测试可注入。
    """
    if session_factory is None:
        from app.core.database import SessionLocal

        session_factory = SessionLocal

    db = session_factory()
    try:
        # 同步写 summary：前端报告页用 summary 展示失败原因
        # （Analysis 响应不含 pipeline_status，只写 error 会导致重新进入时看不到原因）
        db.execute(
            sa_update(Analysis)
            .where(Analysis.id == analysis_id)
            .values(status="failed", summary=(error or "")[:120])
        )
        db.commit()
        log.info("独立连接兜底置 failed 成功 analysis_id={} error={}", analysis_id, error)
    except Exception as exc:  # noqa: BLE001 - 兜底自身绝不允许抛出
        log.error("独立连接兜底置 failed 仍失败 analysis_id={} error={}", analysis_id, exc)
    finally:
        db.close()


class PipelineEngine:
    """管线引擎：编排分析流程

    架构：计算并行 + 写表串行
    - _compute_* 方法在 ThreadPoolExecutor 线程中执行（纯计算，无 DB 操作）
    - _write_* / _update_* 方法在主线程中执行，共用 self.db
    """

    def __init__(self, db: Session, analysis_id: int, session_factory=None):
        self.db = db
        self.analysis_id = analysis_id
        self.max_retries = 3
        self.retry_delay_base = 2  # 指数退避基数
        # 兜底写入用的独立会话工厂（默认 SessionLocal；测试可注入以隔离数据库）
        self._session_factory = session_factory

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
        duration_s: float | None = None,
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
        step_data: dict = {"status": status.value, "ts": time.time()}
        if duration_s is not None:
            step_data["duration_s"] = round(duration_s, 2)
        pipeline_status["steps"][step.value] = step_data
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
        pipeline_start = time.time()
        log.info("管线开始", analysis_id=self.analysis_id)

        try:
            # Step 1: 上传+抽帧
            video_result = self._run_step_with_retry(
                PipelineStep.UPLOAD, self._process_video, video_path, metadata
            )

            # Step 2+3: 并行计算（纯计算，无 DB 操作）
            frame_urls = video_result["frame_urls"]

            # AI 配置在主线程预读，避免线程内使用 DB
            from app.services.config_service import get_ai_config

            ai_config = get_ai_config(self.db)

            parallel_start = time.time()
            with ThreadPoolExecutor(max_workers=2) as executor:
                ai_future = executor.submit(self._compute_ai, frame_urls, metadata, ai_config)
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

            parallel_elapsed = time.time() - parallel_start
            ai_status = "ok" if not ai_exc else type(ai_exc).__name__
            pose_status = "ok" if not pose_exc else type(pose_exc).__name__
            log.info(
                f"管线-并行计算耗时: {parallel_elapsed:.2f}s (ai={ai_status}, pose={pose_status})",
            )

            # Step 2+3 写表：串行执行（共用 self.db）
            write_start = time.time()
            self._update_step_status(PipelineStep.AI, StepStatus.PROCESSING)
            self._write_ai_result(ai_result)
            self._update_step_status(PipelineStep.AI, StepStatus.COMPLETED, progress=100)

            self._update_step_status(PipelineStep.POSE, StepStatus.PROCESSING)
            self._write_pose_result(pose_result)
            self._update_step_status(PipelineStep.POSE, StepStatus.COMPLETED, progress=100)
            write_elapsed = time.time() - write_start
            log.info(f"管线-写表耗时: {write_elapsed:.2f}s")

            # Step 4: 收尾
            self._finalize()

            total_elapsed = time.time() - pipeline_start
            # 写入顶层计时到 pipeline_status
            analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
            if analysis:
                pipeline_status = _parse_pipeline_status(analysis.pipeline_status)
                if pipeline_status:
                    pipeline_status["completed_at"] = time.time()
                    pipeline_status["total_duration_s"] = round(total_elapsed, 2)
                    pipeline_status["parallel_duration_s"] = round(parallel_elapsed, 2)
                    self._update_pipeline_status(pipeline_status)

            log.info(
                f"管线完成 analysis_id={self.analysis_id} total={total_elapsed:.2f}s",
            )
            return {"status": "completed", "ai": ai_result, "pose": pose_result}

        except Exception as e:
            total_elapsed = time.time() - pipeline_start
            # 139：真实异常必须落盘（{} 风格 + 堆栈），禁止 %s 风格（参数会被静默丢弃）
            log.exception(
                "管线失败 analysis_id={} total={:.2f}s error={}",
                self.analysis_id,
                total_elapsed,
                e,
            )
            # 状态兜底（G2）：先修复可能已损坏的连接，再写 failed；仍失败则用独立连接兜底
            try:
                self.db.rollback()
                self._update_step_status(PipelineStep.FINALIZE, StepStatus.FAILED, error=str(e))
                # 同步写 summary（截断），供报告页展示失败原因
                self._update_analysis_field(status="failed", summary=str(e)[:120])
            except Exception as recover_exc:  # noqa: BLE001 - 兜底路径不二次抛出
                log.error(
                    "管线失败态写入失败，启用独立连接兜底 analysis_id={} error={}",
                    self.analysis_id,
                    recover_exc,
                )
                _force_fail(self.analysis_id, str(e), self._session_factory)
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
                    "管线步骤失败 step={} attempt={}/{} error={}: {}",
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
        t0 = time.time()
        from app.services import file_service, video_service

        mode = metadata.get("mode", "single")
        hit_time = metadata.get("hit_time")
        cuts = metadata.get("cuts")

        result = video_service.process_video(video_path, mode, hit_time, cuts)

        user_id = self._get_user_id()
        business = ("analysis", self.analysis_id) if self.analysis_id else None

        # 抽帧中间产物登记为受管文件（{md5}.jpg）
        # 预计算 md5/size：避免 register_batch 内部因 md5s 为空而跳过 existing_map
        # 查询，随后实时算 md5 + INSERT 时撞同 user_id 已存在的 (user_id, md5)
        # 唯一索引（id=17/18 实际现场）。
        try:
            frame_records = file_service.register_batch(
                self.db,
                user_id,
                [
                    file_service.FileDraft(
                        src_path=frame_path,
                        md5=file_service.file_store.md5_of(path=frame_path) if frame_path else "",
                        size=os.path.getsize(frame_path)
                        if frame_path and os.path.exists(frame_path)
                        else 0,
                        ext=os.path.splitext(frame_path)[1] or ".jpg",
                        upload_source="video_frame",
                        original_name=os.path.basename(frame_path),
                    )
                    for frame_path in result.get("frame_paths", [])
                ],
                business=business,
            )
            result["frame_urls"] = [record.rel_path for record in frame_records]
        except Exception:
            # 139：抽帧是致命环节——没有帧，AI 评分与姿态分析就失去输入。
            # 原实现吞异常后置 frame_urls = []，导致后续步骤拿 0 帧空跑，
            # 最终产出"已完成"的垃圾报告（§2.5 路径 A）。改为直接抛出，交由重试处理。
            log.exception("抽帧登记失败(致命) analysis_id={}", self.analysis_id)
            raise

        # 0 帧硬校验：即便登记"成功"但结果为空，同样视为致命
        if not result.get("frame_urls"):
            raise ValueError("抽帧结果为空（0 帧），无法进行 AI 与姿态分析")

        elapsed = time.time() - t0
        n = len(result.get("frame_urls", []))
        t = result.get("trimmed", False)
        log.info(f"管线-视频处理: {elapsed:.1f}s {n}帧 trim={t}")

        # 播放短片纳入文件管理（upload_source=video_playback）并更新 video_url
        if self.analysis_id:
            working_path = result.get("working_path")
            rel_video_url = None
            if working_path:
                try:
                    playback, _ = file_service.register(
                        db=self.db,
                        user_id=user_id,
                        src_path=working_path,
                        category="video_playback",
                        original_name=f"{os.path.basename(working_path)}_playback",
                        ext=os.path.splitext(working_path)[1] or ".mp4",
                        business=business,
                    )
                    rel_video_url = playback.rel_path
                    # 工作路径指向登记后的受管路径，供姿态推理定位
                    result["working_path"] = file_service.abs_of(playback.rel_path)
                except Exception:
                    # 139：播放短片是致命环节——不再用可能无效的路径兜底，
                    # 否则会落库一个指向不存在文件的 video_url（假成功）。
                    log.exception("裁剪视频登记失败(致命) analysis_id={}", self.analysis_id)
                    raise
            self._update_analysis_field(video_url=rel_video_url)

        return result

    def _compute_ai(self, frame_urls: list[str], metadata: dict, ai_config: dict) -> dict:
        """AI 评分（线程内执行，纯计算无 DB）"""
        t0 = time.time()
        import asyncio

        from app.services import ai_service

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

        log.info(f"管线-AI评分耗时: {time.time() - t0:.2f}s frames={len(frame_urls)}")
        return report

    def _compute_pose(self, frame_urls: list[str], video_result: dict, metadata: dict) -> dict:
        """姿态推理（线程内执行，纯计算无 DB）"""
        t0 = time.time()
        from app.services import file_service, pose_service

        save_skeleton = True
        duration = video_result.get("duration")
        frame_rate = video_result.get("frame_rate")
        working_path = video_result.get("working_path")
        video_url = file_service.rel_of(working_path) if working_path else None

        # full 模式强制逐帧生成骨架视频，single 模式按阈值自动判断
        full_frames = True if metadata.get("mode") == "full" else None

        result = pose_service.analyze_frames(
            frames=None,
            video_url=video_url,
            save_skeleton=save_skeleton,
            duration=duration,
            frame_rate=frame_rate,
            frame_urls=frame_urls,
            full_frames=full_frames,
        )

        log.info(f"管线-姿态推理耗时: {time.time() - t0:.2f}s frames={len(frame_urls)}")
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
        """写入姿态结果到数据库（零磁盘 I/O，单次 commit）"""
        if not (self.analysis_id and pose_result):
            return

        from app.services import file_service

        skeleton_video = pose_result.get("skeleton_video_info")
        skeleton_thumb = pose_result.get("skeleton_thumb_info")
        user_id = self._get_user_id()

        # 仅登记骨架视频和缩略图，骨架帧不登记（分析完成后清理）
        all_files = []
        if skeleton_video:
            all_files.append(skeleton_video)
        if skeleton_thumb:
            all_files.append(skeleton_thumb)

        # 登记后物理文件重命名为 {md5}.{后缀}，需把落库路径换成受管路径
        path_map: dict[str, str] = {}
        if all_files:
            try:
                records = file_service.register_batch(
                    self.db,
                    user_id,
                    [
                        file_service.FileDraft(
                            src_path=file_service.abs_of(info["rel_path"]),
                            md5=info.get("md5") or "",
                            size=info.get("size") or 0,
                            ext=os.path.splitext(info["rel_path"])[1],
                            upload_source=info.get("upload_source", ""),
                            original_name=os.path.basename(info["rel_path"]),
                        )
                        for info in all_files
                    ],
                    business=("analysis", self.analysis_id),
                )
                path_map = {
                    info["rel_path"]: record.rel_path
                    for info, record in zip(all_files, records, strict=False)
                }
            except Exception as exc:  # noqa: BLE001 - 骨架登记可降级，打标后继续
                # 139：可降级项——记录日志 + 打标，允许用原始路径继续（不影响最终完成）
                log.warning("文件批量登记失败(可降级): {} - {}", type(exc).__name__, exc)
                self._mark_degraded("skeleton_files", f"骨架文件登记失败: {exc}")

        # 构建 pose JSON：skeleton_frames 为空列表（帧已清理，不落库）
        raw_skeleton_video = pose_result.get("skeleton_video_url")
        skeleton_video_path = path_map.get(raw_skeleton_video or "", raw_skeleton_video)
        skeleton_thumb_path = path_map.get(
            skeleton_thumb["rel_path"] if skeleton_thumb else "",
            skeleton_thumb["rel_path"] if skeleton_thumb else None,
        )
        pose_for_db = {
            "frames": pose_result.get("frames"),
            "metrics": pose_result.get("metrics"),
            "detected": pose_result.get("detected"),
            "skeleton_frames": [],
            "skeleton_video_url": skeleton_video_path,
        }
        if skeleton_thumb_path:
            pose_for_db["skeleton_thumb"] = skeleton_thumb_path
        stmt = (
            sa_update(Analysis)
            .where(Analysis.id == self.analysis_id)
            .values(
                pose=json.dumps(pose_for_db, ensure_ascii=False),
                thumb=skeleton_thumb_path,
            )
        )
        self.db.execute(stmt)
        self.db.commit()

    def _finalize(self) -> None:
        """收尾更新状态"""
        t0 = time.time()
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
                    "duration_s": round(time.time() - t0, 2),
                }
                self._update_pipeline_status(pipeline_status)

            # 清理中间帧文件（抽样帧 _f*.jpg + 骨架帧 _sk*.jpg）
            self._cleanup_intermediate_frames(analysis.video_url)
        else:
            # 139：原实现仅 warn 后保留 processing 孤儿，导致前端无限轮询（§2.5 路径 B）。
            # 改为明确置 failed 并写入错误原因。
            log.error("分析记录 video_url 为空，置为 failed analysis_id={}", self.analysis_id)
            self._update_analysis_field(status="failed", summary="播放短片缺失，分析未完成")
            self._update_step_status(
                PipelineStep.FINALIZE,
                StepStatus.FAILED,
                error="播放短片缺失，分析未完成",
            )

    def _mark_degraded(self, item: str, reason: str) -> None:
        """可降级项打标：保留完成能力，但必须可观测（139 决策 10）

        写入 `pipeline_status.degraded` 列表，避免"无痕降级"——
        降级后的报告仍可用，但需在状态里留下记录以便排查。
        """
        try:
            analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
            if not analysis:
                return
            pipeline_status = _parse_pipeline_status(analysis.pipeline_status)
            if pipeline_status is None:
                pipeline_status = _initial_pipeline_status()
            degraded = pipeline_status.setdefault("degraded", [])
            degraded.append({"item": item, "reason": reason})
            self._update_pipeline_status(pipeline_status)
        except Exception as exc:  # noqa: BLE001 - 打标失败不得影响主流程
            log.warning("降级标记写入失败 item={} error={}", item, exc)

    def _cleanup_intermediate_frames(self, video_url: str) -> None:
        """删除中间帧文件（_f*.jpg 抽样帧 + _sk*.jpg 骨架帧）"""
        import glob

        from app.services import file_service

        video_dir = os.path.dirname(file_service.abs_of(video_url))
        cleaned = 0

        # 受管文件已按 {md5} 命名，残留的 _f* / _sk* 均为未登记的中间产物
        for pattern in ("*_f*.jpg", "*_sk*.jpg"):
            for path in glob.glob(os.path.join(video_dir, pattern)):
                try:
                    os.remove(path)
                    cleaned += 1
                except OSError as exc:
                    log.warning("删除中间帧失败: {} - {}", path, exc)

        if cleaned:
            log.info("已清理中间帧: {} 个文件 business=analysis/{}", cleaned, self.analysis_id)
