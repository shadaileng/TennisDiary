"""装备管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.gear import Gear
from app.schemas.admin import GearAdminResponse, PaginatedResponse

router = APIRouter(prefix="/api/admin/gears", tags=["admin-gears"])


@router.get("", response_model=PaginatedResponse[GearAdminResponse])
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
    gears = query.order_by(Gear.id.desc()).offset(offset).limit(limit).all()
    return PaginatedResponse(
        items=[GearAdminResponse.model_validate(g) for g in gears],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{gear_id}", response_model=GearAdminResponse)
def get_gear(
    gear_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """装备详情"""
    gear = db.query(Gear).filter(Gear.id == gear_id).first()
    if gear is None:
        raise HTTPException(status_code=404, detail="装备不存在")
    return GearAdminResponse.model_validate(gear)


@router.delete("/{gear_id}")
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
    return {"message": "删除成功"}
