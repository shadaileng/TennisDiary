"""分析管理路由"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.decorators.audit import audit
from app.models.admin import Admin
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.admin import AnalysisAdminResponse, AnalysisDetailAdminResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/analyses", tags=["admin-analyses"])


def _enrich_analysis(a: Analysis, db: Session) -> AnalysisAdminResponse:
    resp = AnalysisAdminResponse.model_validate(a)
    user = db.query(User).filter(User.id == a.user_id).first()
    if user:
        resp.user = {"id": user.id, "nickname": user.nickname or ""}
    return resp


def _parse_json_field(raw: str | None) -> dict | list | None:
    """容错解析 JSON 字段：非法 JSON / 空值返回 None（兼容历史脏数据）"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


@router.get("", response_model=ApiResponse[PaginatedData[AnalysisAdminResponse]])
def list_analyses(
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """分析报告列表（分页+用户筛选）"""
    query = db.query(Analysis)
    if user_id is not None:
        query = query.filter(Analysis.user_id == user_id)

    total = query.count()
    analyses = query.order_by(Analysis.date.desc()).offset(offset).limit(limit).all()
    return ApiResponse(
        data=PaginatedData(
            items=[_enrich_analysis(a, db) for a in analyses],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{analysis_id}", response_model=ApiResponse[AnalysisDetailAdminResponse])
def get_analysis(
    analysis_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """分析详情（含完整六维报告 / 封面 / 高光帧）"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="分析报告不存在")

    resp = _enrich_analysis(analysis, db)
    report = _parse_json_field(analysis.report)
    highlights = _parse_json_field(analysis.highlights)
    pose = _parse_json_field(analysis.pose)
    detail = AnalysisDetailAdminResponse(
        **resp.model_dump(),
        report=report if isinstance(report, dict) else None,
        highlights=highlights if isinstance(highlights, list) else None,
        video_url=analysis.video_url,
        pose=pose if isinstance(pose, dict) else None,
    )
    return ApiResponse(data=detail)


@router.delete("/{analysis_id}", response_model=ApiResponse[None])
@audit(action="DELETE", resource_type="analysis", resource_id_key="analysis_id")
def delete_analysis(
    analysis_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除分析报告"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="分析报告不存在")

    db.delete(analysis)
    db.commit()
    return ApiResponse(message="删除成功")
