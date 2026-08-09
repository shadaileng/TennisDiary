"""体重管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.models.weight import WeightRecord
from app.schemas.admin import WeightAdminResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/weights", tags=["admin-weights"])


def _enrich_weight(w: WeightRecord, db: Session) -> WeightAdminResponse:
    resp = WeightAdminResponse.model_validate(w)
    user = db.query(User).filter(User.id == w.user_id).first()
    if user:
        resp.user = {"id": user.id, "nickname": user.nickname or ""}
    return resp


@router.get("", response_model=ApiResponse[PaginatedData[WeightAdminResponse]])
def list_weights(
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """体重记录列表（分页+用户筛选）"""
    query = db.query(WeightRecord)
    if user_id is not None:
        query = query.filter(WeightRecord.user_id == user_id)

    total = query.count()
    weights = query.order_by(WeightRecord.created_at.desc()).offset(offset).limit(limit).all()
    return ApiResponse(
        data=PaginatedData(
            items=[_enrich_weight(w, db) for w in weights],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.delete("/{weight_id}", response_model=ApiResponse[None])
def delete_weight(
    weight_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除体重记录"""
    weight = db.query(WeightRecord).filter(WeightRecord.id == weight_id).first()
    if weight is None:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(weight)
    db.commit()
    return ApiResponse(message="删除成功")
