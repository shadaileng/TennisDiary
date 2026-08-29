"""用户端分析报告路由：落库 / 历史列表 / 详情 / 删除"""

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
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

    # 批量注册文件
    if files_to_register:
        file_service.register_ai_files(
            db=db,
            user_id=current_user.id,
            paths=files_to_register,
            business_type="analysis",
            business_id=analysis.id,
        )

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
