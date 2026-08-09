"""装备管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.gear import Gear
from app.models.user import User
from app.schemas.admin import GearAdminResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/gears", tags=["admin-gears"])


def _enrich_gear(g: Gear, db: Session) -> GearAdminResponse:
    resp = GearAdminResponse.model_validate(g)
    user = db.query(User).filter(User.id == g.user_id).first()
    if user:
        resp.user = {"id": user.id, "nickname": user.nickname or ""}
    return resp


@router.get("", response_model=ApiResponse[PaginatedData[GearAdminResponse]])
def list_gears(
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """装备列表（分页+用户筛选）"""
    query = db.query(Gear)
    if user_id is not None:
        query = query.filter(Gear.user_id == user_id)

    total = query.count()
    gears = query.order_by(Gear.created_at.desc()).offset(offset).limit(limit).all()
    return ApiResponse(
        data=PaginatedData(
            items=[_enrich_gear(g, db) for g in gears],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{gear_id}", response_model=ApiResponse[GearAdminResponse])
def get_gear(
    gear_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """装备详情"""
    gear = db.query(Gear).filter(Gear.id == gear_id).first()
    if gear is None:
        raise HTTPException(status_code=404, detail="装备不存在")
    return ApiResponse(data=GearAdminResponse.model_validate(gear))


@router.delete("/{gear_id}", response_model=ApiResponse[None])
def delete_gear(
    gear_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除装备"""
    gear = db.query(Gear).filter(Gear.id == gear_id).first()
    if gear is None:
        raise HTTPException(status_code=404, detail="装备不存在")

    db.delete(gear)
    db.commit()
    return ApiResponse(message="删除成功")
