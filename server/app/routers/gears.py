"""装备相关路由：列表 / 添加 / 详情 / 编辑 / 删除"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.gear import Gear
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.schemas import GearCreate, GearResponse, GearUpdate

log = get_logger("user")

router = APIRouter(prefix="/api/gears", tags=["gears"])


def _get_owned_gear(db: Session, gear_id: int, user: User) -> Gear:
    """获取属于当前用户的装备，不存在或越权返回 404"""
    gear = db.query(Gear).filter(Gear.id == gear_id, Gear.user_id == user.id).first()
    if gear is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="装备不存在")
    return gear


@router.get("", response_model=ApiResponse[list[GearResponse]])
def list_gears(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的装备列表，按创建时间倒序"""
    gears = (
        db.query(Gear)
        .filter(Gear.user_id == current_user.id)
        .order_by(Gear.created_at.desc())
        .all()
    )
    return ApiResponse(data=[GearResponse.model_validate(g) for g in gears])


@router.post("", response_model=ApiResponse[GearResponse], status_code=status.HTTP_200_OK)
def create_gear(
    body: GearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加装备"""
    import time

    gear = Gear(
        user_id=current_user.id,
        category=body.category,
        name=body.name,
        buy_date=body.buy_date,
        price=body.price,
        feeling=body.feeling,
        photo=body.photo,
        created_at=time.time(),
    )
    db.add(gear)
    db.commit()
    db.refresh(gear)
    log.info("添加装备成功", user_id=current_user.id, gear_id=gear.id)
    return ApiResponse(data=GearResponse.model_validate(gear))


@router.get("/{gear_id}", response_model=ApiResponse[GearResponse])
def get_gear(
    gear_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """装备详情"""
    return ApiResponse(data=GearResponse.model_validate(_get_owned_gear(db, gear_id, current_user)))


@router.put("/{gear_id}", response_model=ApiResponse[GearResponse])
def update_gear(
    gear_id: int,
    body: GearUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑装备 — 仅更新传入的字段"""
    gear = _get_owned_gear(db, gear_id, current_user)

    if body.category is not None:
        gear.category = body.category
    if body.name is not None:
        gear.name = body.name
    if body.buy_date is not None:
        gear.buy_date = body.buy_date
    if body.price is not None:
        gear.price = body.price
    if body.feeling is not None:
        gear.feeling = body.feeling
    if body.photo is not None:
        gear.photo = body.photo

    db.commit()
    db.refresh(gear)
    log.info("更新装备成功", user_id=current_user.id, gear_id=gear.id)
    return ApiResponse(data=GearResponse.model_validate(gear))


@router.delete("/{gear_id}", response_model=ApiResponse[None], status_code=status.HTTP_200_OK)
def delete_gear(
    gear_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除装备"""
    gear = _get_owned_gear(db, gear_id, current_user)
    db.delete(gear)
    db.commit()
    log.info("删除装备成功", user_id=current_user.id, gear_id=gear_id)
    return ApiResponse(message="删除成功")
