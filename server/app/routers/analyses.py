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
    File,
    Form,
    HTTPException,
    UploadFile,
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
    AnalysisUpdate,
)
from app.services import file_service

log = get_logger("user")

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def _parse_json_field(raw: str | None) -> dict | list | None:
    """容错解析 JSON 字段：非法 JSON / 空值返回 None（兼容历史脏数据）"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def analysis_to_response(analysis: Analysis) -> AnalysisResponse:
    """将 ORM Analysis 转换为 AnalysisResponse，report/highlights/pose 转结构化 JSON"""
    report = _parse_json_field(analysis.report)
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

    # 批量注册文件（统一使用 get_or_create_file，每文件 savepoint 隔离）
    if files_to_register:
        for rel_path in files_to_register:
            abs_path = file_service.rel_path_to_abs(rel_path)
            if not os.path.exists(abs_path):
                log.warning("文件不存在，跳过登记", rel_path=rel_path)
                continue
            try:
                with db.begin_nested():
                    source = "video" if rel_path == body.video_url else "skeleton"
                    file_service.get_or_create_file(
                        db=db,
                        user_id=current_user.id,
                        rel_path=rel_path,
                        abs_path=abs_path,
                        upload_source=source,
                        original_name=os.path.basename(rel_path),
                    )
            except Exception as e:  # noqa: BLE001 - 文件登记失败不应阻断流程
                log.warning("文件登记失败", rel_path=rel_path, error=type(e).__name__)

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
    """删除分析报告（同时递减所有关联文件引用计数：视频、帧、骨架产物）"""
    analysis = _get_owned_analysis(db, analysis_id, current_user)

    # 递减所有关联文件的引用计数
    file_service.decrement_analysis_files(db, analysis)

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


async def _save_uploaded_file(file: UploadFile, user_id: int) -> str:
    """保存上传的视频文件到磁盘，返回绝对路径"""
    from app.core.config import settings

    upload_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), "videos", str(user_id))
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    filename = f"{int(time.time() * 1000)}_{os.urandom(4).hex()}{ext}"
    file_path = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


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
async def start_analysis(
    file: UploadFile = File(...),
    date: str = Form(...),
    kind: str = Form(default="综合"),
    mode: str = Form(default="single"),
    hit_time: float = Form(default=0.0),
    cuts: str | None = Form(default=None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """统一分析端点：上传视频并启动后台分析管线

    - 创建 Analysis 占位记录（status=processing）
    - 保存视频文件
    - 后台异步执行完整管线（upload → ai ∥ pose → finalize）
    - 返回 analysis_id 和初始管线状态，前端通过轮询/SSE 获取进度
    """
    # 1. 创建 Analysis 记录
    pipeline_status = _initial_pipeline_status()
    analysis = Analysis(
        user_id=current_user.id,
        date=date,
        kind=kind,
        mode=mode,
        status="processing",
        pipeline_status=json.dumps(pipeline_status, ensure_ascii=False),
        created_at=time.time(),
    )
    db.add(analysis)
    db.flush()
    db.refresh(analysis)
    analysis_id = analysis.id

    # 2. 保存视频文件
    video_path = await _save_uploaded_file(file, current_user.id)

    # 3. 文件纳入管理（统一使用 get_or_create_file）
    from app.services import file_service

    rel_video = file_service.abs_path_to_rel(video_path)
    file_service.get_or_create_file(
        db=db,
        user_id=current_user.id,
        rel_path=rel_video,
        abs_path=video_path,
        upload_source="video",
        original_name=file.filename or "video.mp4",
        mime_type=file.content_type or "",
    )
    db.commit()

    # 4. 解析 cuts
    cuts_list = None
    if cuts:
        try:
            cuts_list = json.loads(cuts)
        except (json.JSONDecodeError, TypeError):
            log.warning("cuts JSON 解析失败", cuts=cuts)

    # 4. 启动后台任务
    metadata = {
        "date": date,
        "kind": kind,
        "mode": mode,
        "hit_time": hit_time,
        "cuts": cuts_list,
    }
    background_tasks.add_task(_run_analysis_pipeline, analysis_id, video_path, metadata)

    log.info("统一分析端点已触发", user_id=current_user.id, analysis_id=analysis_id)
    return ApiResponse(
        data={
            "id": analysis_id,
            "status": "processing",
            "pipeline_status": pipeline_status,
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
