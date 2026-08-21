"""体重记录相关路由：列表 / 添加 / 删除"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.user import User
from app.models.weight import WeightRecord
from app.schemas.common import ApiResponse
from app.schemas.schemas import WeightCreate, WeightResponse

log = get_logger("user")

router = APIRouter(prefix="/api/weights", tags=["weights"])


def _get_owned_weight(db: Session, weight_id: int, user: User) -> WeightRecord:
    """获取属于当前用户的体重记录，不存在或越权返回 404"""
    record = (
        db.query(WeightRecord)
        .filter(WeightRecord.id == weight_id, WeightRecord.user_id == user.id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="体重记录不存在")
    return record


@router.get("", response_model=ApiResponse[list[WeightResponse]])
def list_weights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的体重记录列表，按创建时间倒序"""
    records = (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == current_user.id)
        .order_by(WeightRecord.created_at.desc())
        .all()
    )
    return ApiResponse(data=[WeightResponse.model_validate(r) for r in records])


@router.post("", response_model=ApiResponse[WeightResponse], status_code=status.HTTP_200_OK)
@audit(action="CREATE", resource_type="weight")
def create_weight(
    body: WeightCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加体重记录"""
    import time

    record = WeightRecord(
        user_id=current_user.id,
        date=body.date,
        weight=body.weight,
        bust=body.bust,
        waist=body.waist,
        hip=body.hip,
        created_at=time.time(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log.info("添加体重记录成功", user_id=current_user.id, weight_id=record.id)
    return ApiResponse(data=WeightResponse.model_validate(record))


@router.delete("/{weight_id}", response_model=ApiResponse[None], status_code=status.HTTP_200_OK)
@audit(action="DELETE", resource_type="weight", resource_id_key="weight_id")
def delete_weight(
    weight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除体重记录"""
    record = _get_owned_weight(db, weight_id, current_user)
    db.delete(record)
    db.commit()
    log.info("删除体重记录成功", user_id=current_user.id, weight_id=weight_id)
    return ApiResponse(message="删除成功")
