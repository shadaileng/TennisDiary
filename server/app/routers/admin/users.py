"""用户管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.schemas.admin import PaginatedResponse, UserAdminResponse

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


@router.get("", response_model=PaginatedResponse[UserAdminResponse])
def list_users(
    offset: int = 0,
    limit: int = 20,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户列表（分页）"""
    total = db.query(User).count()
    users = db.query(User).offset(offset).limit(limit).all()
    return PaginatedResponse(
        items=[UserAdminResponse.model_validate(u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserAdminResponse)
def get_user(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserAdminResponse.model_validate(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.delete(user)
    db.commit()
    return {"message": "删除成功"}
