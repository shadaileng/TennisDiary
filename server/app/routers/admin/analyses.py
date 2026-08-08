"""分析管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.analysis import Analysis
from app.schemas.admin import AnalysisAdminResponse, PaginatedResponse

router = APIRouter(prefix="/api/admin/analyses", tags=["admin-analyses"])


@router.get("", response_model=PaginatedResponse[AnalysisAdminResponse])
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
    return PaginatedResponse(
        items=[AnalysisAdminResponse.model_validate(a) for a in analyses],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{analysis_id}", response_model=AnalysisAdminResponse)
def get_analysis(
    analysis_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """分析详情"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="分析报告不存在")
    return AnalysisAdminResponse.model_validate(analysis)


@router.delete("/{analysis_id}")
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
    return {"message": "删除成功"}
