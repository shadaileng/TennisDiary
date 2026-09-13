"""用户端分析报告路由：落库 / 历史列表 / 详情 / 删除 / 统一分析端点 / 状态查询 / SSE推送"""

import asyncio
import json
import os
import time
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.schemas import (
    AnalysisCreate,
    AnalysisInitRequest,
    AnalysisResponse,
    AnalysisStartRequest,
    AnalysisUpdate,
)
from app.services import file_service

log = get_logger("user")

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

# 启动分析只接受来源为 video 的受管文件
_VIDEO_SOURCE = "video"


def _parse_json_field(raw: str | None) -> dict | list | None:
    """容错解析 JSON 字段：非法 JSON / 空值返回 None（兼容历史脏数据）"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


_DIMENSION_KEY_ALIASES: dict[str, str] = {"command": "comment"}


def _normalize_dimensions(report: dict) -> None:
    """归一化 dimensions 中 AI 拼写错误的字段别名（如 command → comment）"""
    dims = report.get("dimensions")
    if not isinstance(dims, list):
        return
    for d in dims:
        for alias, canonical in _DIMENSION_KEY_ALIASES.items():
            if alias in d and canonical not in d:
                d[canonical] = d.pop(alias)


def analysis_to_response(analysis: Analysis) -> AnalysisResponse:
    """将 ORM Analysis 转换为 AnalysisResponse，report/highlights/pose 转结构化 JSON"""
    report = _parse_json_field(analysis.report)
    if isinstance(report, dict):
        _normalize_dimensions(report)
    highlights = _parse_json_field(analysis.highlights)
    pose = _parse_json_field(analysis.pose)
    return AnalysisResponse(
        id=analysis.id,
        user_id=analysis.user_id,
        date=analysis.date,
        kind=analysis.kind,
        mode=analysis.mode,
        score=analysis.score,
        summary=analysis.summary,
        ntrp=analysis.ntrp,
        report=report if isinstance(report, dict) else None,
        thumb=analysis.thumb,
        highlights=highlights if isinstance(highlights, list) else None,
        video_url=analysis.video_url,
        pose=pose if isinstance(pose, dict) else None,
        status=analysis.status,
        created_at=analysis.created_at,
    )


def _get_owned_analysis(db: Session, analysis_id: int, user: User) -> Analysis:
    """获取属于当前用户的分析，不存在或越权返回 404"""
    analysis = (
        db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析报告不存在")
    return analysis


@router.post("/init", response_model=ApiResponse[dict])
@audit(action="INIT", resource_type="analysis")
def init_analysis(
    body: AnalysisInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析初始化（118 流水线步骤1）：仅建 Analysis 占位记录，返回 analysis_id"""
    analysis = Analysis(
        user_id=current_user.id,
        date=body.date,
        kind=body.kind,
        mode=body.mode,
        status="processing",
        created_at=time.time(),
    )
    db.add(analysis)
    db.flush()
    db.refresh(analysis)
    log.info("分析记录初始化成功", user_id=current_user.id, analysis_id=analysis.id)
    return ApiResponse(data={"id": analysis.id})


def _infer_file_source(rel_path: str, video_url: str | None, thumb: str | None) -> str:
    """推断登记文件的 upload_source（131：细化骨架/封面来源，支撑文件分类）

    此前除 video_url 外一律登记为 skeleton，封面、骨架视频、骨架帧混为一谈，
    分类时无法区分。细化后各来源均落在 file_service.ANALYSIS_MATCH_SOURCES 内，
    分类行为与原先一致但更准确。
    """
    if video_url and rel_path == video_url:
        return "video"
    if thumb and rel_path == thumb:
        return "analysis_thumb"
    name = os.path.basename(rel_path).lower()
    if name.endswith("_skeleton.mp4"):
        return "skeleton_video"
    if name.endswith(("_thumb.jpg", "_thumb.jpeg", "_thumb.png")):
        return "skeleton_thumb"
    if name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "skeleton_frame"
    return "skeleton"


@router.post("", response_model=ApiResponse[AnalysisResponse])
@audit(action="CREATE", resource_type="analysis")
def create_analysis(
    body: AnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """落库分析报告：AI 分析成功后调用，供历史回看（同时注册所有关联文件到 File 表）"""
    analysis = Analysis(
        user_id=current_user.id,
        date=body.date,
        kind=body.kind,
        mode=body.mode,
        status="completed",
        score=body.score,
        summary=body.summary,
        ntrp=body.ntrp,
        report=json.dumps(body.report.model_dump(), ensure_ascii=False) if body.report else None,
        thumb=body.thumb,
        highlights=json.dumps(body.highlights, ensure_ascii=False) if body.highlights else None,
        video_url=body.video_url,
        pose=json.dumps(body.pose, ensure_ascii=False) if body.pose else None,
        created_at=time.time(),
    )
    db.add(analysis)
    db.flush()  # 获取 analysis.id

    # 收集所有需要注册的文件路径
    files_to_register = []
    if body.thumb:
        files_to_register.append(body.thumb)
    if body.video_url:
        files_to_register.append(body.video_url)
    if body.highlights and isinstance(body.highlights, list):
        files_to_register.extend(body.highlights)
    # 骨架产物（从 pose JSON 提取）
    if body.pose and isinstance(body.pose, dict):
        skeleton_frames = body.pose.get("skeleton_frames") or []
        files_to_register.extend(skeleton_frames)
        skeleton_video = body.pose.get("skeleton_video_url")
        if skeleton_video:
            files_to_register.append(skeleton_video)
        skeleton_thumb = body.pose.get("skeleton_thumb")
        if skeleton_thumb:
            files_to_register.append(skeleton_thumb)

    # 登记并绑定到该分析记录（已登记的文件按 MD5 命中复用，仅补绑定）
    for rel_path in dict.fromkeys(files_to_register):
        if not file_service.exists(rel_path):
            log.warning("文件不存在，跳过登记", rel_path=rel_path)
            continue
        try:
            with db.begin_nested():
                source = _infer_file_source(rel_path, body.video_url, body.thumb)
                file_service.register(
                    db=db,
                    user_id=current_user.id,
                    src_path=file_service.abs_of(rel_path),
                    category=source,
                    original_name=os.path.basename(rel_path),
                    ext=os.path.splitext(rel_path)[1],
                    business=("analysis", analysis.id),
                )
        except Exception as exc:  # noqa: BLE001 - 文件登记失败不应阻断流程
            log.warning("文件登记失败", rel_path=rel_path, error=type(exc).__name__)

    db.commit()
    db.refresh(analysis)
    log.info("分析报告落库成功", user_id=current_user.id, analysis_id=analysis.id)
    return ApiResponse(data=analysis_to_response(analysis))


@router.get("", response_model=ApiResponse[PaginatedData[AnalysisResponse]])
def list_analyses(
    offset: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的历史分析报告列表，按创建时间倒序分页"""
    # 139：惰性清理孤儿 processing 记录（带节流），避免列表里出现永不结束的"分析中"
    from app.services.analysis_cleanup import maybe_cleanup_stuck_processing

    maybe_cleanup_stuck_processing(db)

    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    total = query.count()
    analyses = query.order_by(Analysis.created_at.desc()).offset(offset).limit(limit).all()
    return ApiResponse(
        data=PaginatedData(
            items=[analysis_to_response(a) for a in analyses],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{analysis_id}", response_model=ApiResponse[AnalysisResponse])
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析报告详情（含完整六维报告结构化 JSON）"""
    analysis = _get_owned_analysis(db, analysis_id, current_user)
    return ApiResponse(data=analysis_to_response(analysis))


@router.put("/{analysis_id}", response_model=ApiResponse[AnalysisResponse])
@audit(action="UPDATE", resource_type="analysis", resource_id_key="analysis_id")
def finalize_analysis(
    analysis_id: int,
    body: AnalysisUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析收尾（118 流水线步骤5）：置 status=completed 并返回完整记录。
    幂等：重复调用安全；仅当 video_url 非空才真正完成（否则保留 processing 孤儿）。
    """
    analysis = _get_owned_analysis(db, analysis_id, current_user)
    if body.status == "completed":
        # 仅当 video_url 非空（步骤2 已产出可播放内容）才真正完成；
        # 否则保留 processing 孤儿记录（符合"不加清理"约定）。
        if analysis.video_url:
            stmt = sa_update(Analysis).where(Analysis.id == analysis_id).values(status="completed")
            db.execute(stmt)
            db.commit()
            db.refresh(analysis)
            log.info("分析记录已收尾", user_id=current_user.id, analysis_id=analysis_id)
        else:
            db.commit()
            log.warning(
                "分析记录 video_url 为空，保留 processing 孤儿",
                user_id=current_user.id,
                analysis_id=analysis_id,
            )
    else:
        db.commit()
    return ApiResponse(data=analysis_to_response(analysis))


@router.delete("/{analysis_id}", response_model=ApiResponse[Any])
@audit(action="DELETE", resource_type="analysis", resource_id_key="analysis_id")
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除分析报告（同时解除所有关联文件的业务绑定：视频、帧、骨架产物）"""
    analysis = _get_owned_analysis(db, analysis_id, current_user)

    # 解除分析记录引用的全部文件绑定（ref_count 自动 -1）
    file_service.unbind_record(db, "analysis", analysis.id)
    # 兜底清理登记后残留的中间产物（_f*.jpg / _sk*.jpg）
    file_service.cleanup_intermediates(current_user.id)

    db.delete(analysis)
    db.commit()
    log.info("删除分析报告成功", user_id=current_user.id, analysis_id=analysis_id)
    return ApiResponse(message="删除成功")


# ==================== 统一分析端点（119） ====================


def _initial_pipeline_status() -> dict:
    """初始化管线状态"""
    from app.services.pipeline import PipelineStep

    return {
        "step": "init",
        "progress": 0,
        "steps": {step.value: {"status": "pending"} for step in PipelineStep},
        "error": None,
        "retry_count": 0,
    }


def _run_analysis_pipeline(analysis_id: int, video_path: str, metadata: dict) -> None:
    """后台任务：执行分析管线（sync def → FastAPI 放入线程池，不阻塞事件循环）"""
    from app.core.database import SessionLocal
    from app.services.pipeline import PipelineEngine

    db = SessionLocal()
    try:
        engine = PipelineEngine(db, analysis_id)
        engine.run_pipeline(video_path, metadata)
    finally:
        db.close()


@router.post("/start", response_model=ApiResponse[dict])
@audit(action="START", resource_type="analysis")
def start_analysis(
    body: AnalysisStartRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """统一分析端点：凭已上传视频的 file_id 启动后台分析管线（137 阶段一）

    - 校验 file_id 归属当前用户、来源为 video、物理文件仍在
    - 创建 Analysis 占位记录（status=processing）+ 绑定源文件（field=source）
    - 后台异步执行完整管线（upload → ai ∥ pose → finalize）
    - 返回 analysis_id 与初始管线状态，前端通过轮询/SSE 获取进度
    """
    # 1. 校验并定位已上传的视频文件（越权/失效一律 404，前端据此降级重传）
    record = file_service.find_by_id(db, current_user.id, body.file_id)
    if record is None or record.upload_source != _VIDEO_SOURCE:
        log.warning(
            "启动分析失败：文件不存在或来源非法",
            user_id=current_user.id,
            file_id=body.file_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="视频文件不存在或无权访问"
        )

    if not file_service.exists(record.rel_path):
        log.warning(
            "启动分析失败：物理文件缺失",
            user_id=current_user.id,
            file_id=record.id,
            rel_path=record.rel_path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="视频文件已失效，请重新上传"
        )

    video_path = file_service.abs_of(record.rel_path)

    # 2. 创建 Analysis 记录
    pipeline_status = _initial_pipeline_status()
    analysis = Analysis(
        user_id=current_user.id,
        date=body.date,
        kind=body.kind,
        mode=body.mode,
        status="processing",
        pipeline_status=json.dumps(pipeline_status, ensure_ascii=False),
        created_at=time.time(),
    )
    db.add(analysis)
    db.flush()
    db.refresh(analysis)
    analysis_id = analysis.id

    # 3. 绑定源文件到该分析记录（ref_count +1）
    file_service.bind(db, current_user.id, record.rel_path, "analysis", analysis_id, field="source")
    db.commit()

    # 4. 启动后台任务
    metadata = {
        "date": body.date,
        "kind": body.kind,
        "mode": body.mode,
        "hit_time": body.hit_time,
        "cuts": body.cuts,
    }
    background_tasks.add_task(_run_analysis_pipeline, analysis_id, video_path, metadata)

    log.info(
        "统一分析端点已触发",
        user_id=current_user.id,
        analysis_id=analysis_id,
        file_id=record.id,
    )
    return ApiResponse(
        data={
            "id": analysis_id,
            "status": "processing",
            "pipeline_status": pipeline_status,
            "file_id": record.id,
        }
    )


# ==================== 状态查询端点（119） ====================


def _analysis_to_status_response(analysis: Analysis) -> dict:
    """将 Analysis 转换为状态查询响应"""
    pipeline_status = _parse_json_field(analysis.pipeline_status)
    return {
        "id": analysis.id,
        "status": analysis.status,
        "pipeline_status": pipeline_status,
    }


@router.get("/{analysis_id}/status", response_model=ApiResponse[dict])
def get_analysis_status(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询分析管线状态（供前端轮询）"""
    analysis = _get_owned_analysis(db, analysis_id, current_user)
    return ApiResponse(data=_analysis_to_status_response(analysis))


# ==================== SSE 推送端点（119） ====================


@router.get("/{analysis_id}/stream")
async def stream_analysis_status(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE 实时推送分析状态（供前端高级模式订阅）"""

    async def event_generator():
        last_status = None
        poll_interval = 1.0  # SSE 模式下轮询间隔更短

        while True:
            # 查询最新状态
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis is None or analysis.user_id != current_user.id:
                yield f"data: {json.dumps({'error': '分析记录不存在'})}\n\n"
                break

            current_status = {
                "step": None,
                "progress": 0,
                "steps": {},
            }
            if analysis.pipeline_status:
                try:
                    ps = json.loads(analysis.pipeline_status)
                    current_status = {
                        "step": ps.get("step"),
                        "progress": ps.get("progress", 0),
                        "steps": ps.get("steps", {}),
                    }
                except (json.JSONDecodeError, TypeError):
                    pass

            # 状态变更时推送
            status_key = f"{current_status['step']}_{current_status['progress']}"
            if status_key != last_status:
                yield f"data: {json.dumps(current_status, ensure_ascii=False)}\n\n"
                last_status = status_key

            # 完成或失败时结束
            if analysis.status in ("completed", "failed"):
                yield f"data: {json.dumps({'status': analysis.status})}\n\n"
                break

            # 轮询间隔
            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
