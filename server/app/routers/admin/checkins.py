"""打卡管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.checkin import Checkin
from app.schemas.admin import CheckinAdminResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/checkins", tags=["admin-checkins"])


@router.get("", response_model=ApiResponse[PaginatedData[CheckinAdminResponse]])
def list_checkins(
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """打卡记录列表（分页+用户筛选）"""
    query = db.query(Checkin)
    if user_id is not None:
        query = query.filter(Checkin.user_id == user_id)

    total = query.count()
    checkins = query.order_by(Checkin.date.desc()).offset(offset).limit(limit).all()
    return ApiResponse(
        data=PaginatedData(
            items=[CheckinAdminResponse.model_validate(c) for c in checkins],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.delete("/{checkin_id}", response_model=ApiResponse[None])
def delete_checkin(
    checkin_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除打卡记录"""
    checkin = db.query(Checkin).filter(Checkin.id == checkin_id).first()
    if checkin is None:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(checkin)
    db.commit()
    return ApiResponse(message="删除成功")
