"""管理员认证路由"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import create_admin_access_token, get_current_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.admin import Admin
from app.schemas.admin import (
    AdminAuthResetRequest,
    AdminLoginRequest,
    AdminPasswordUpdate,
    AdminResponse,
    AdminTokenResponse,
    MessageResponse,
    RoleResponse,
)

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=AdminTokenResponse)
def admin_login(body: AdminLoginRequest, db: Session = Depends(get_db)):
    """管理员登录（账号密码）"""
    admin = db.query(Admin).filter(Admin.username == body.username).first()
    if admin is None or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 更新最后登录时间
    admin.last_login = datetime.utcnow()
    db.commit()

    # 构建响应
    role_resp = RoleResponse.from_orm(admin.role) if admin.role else None
    admin_resp = AdminResponse(
        id=admin.id,
        username=admin.username,
        nickname=admin.nickname or "",
        role=role_resp,
        is_active=admin.is_active,
        last_login=admin.last_login,
        created_at=admin.created_at,
    )

    token = create_admin_access_token(admin.id)
    return AdminTokenResponse(
        access_token=token,
        admin=admin_resp,
    )


@router.get("/me", response_model=AdminResponse)
def get_admin_info(admin: Admin = Depends(get_current_admin)):
    """获取当前管理员信息"""
    role_resp = RoleResponse.from_orm(admin.role) if admin.role else None
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        nickname=admin.nickname or "",
        role=role_resp,
        is_active=admin.is_active,
        last_login=admin.last_login,
        created_at=admin.created_at,
    )


@router.put("/password", response_model=MessageResponse)
def update_password(
    body: AdminPasswordUpdate,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """修改密码"""
    if not verify_password(body.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    admin.password_hash = hash_password(body.new_password)
    db.commit()
    return MessageResponse(message="密码修改成功")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: AdminAuthResetRequest, db: Session = Depends(get_db)):
    """通过密钥重置管理员密码（忘记密码时使用）"""
    if not settings.ADMIN_RESET_KEY:
        raise HTTPException(status_code=403, detail="密码重置功能未启用")
    if body.reset_key != settings.ADMIN_RESET_KEY:
        raise HTTPException(status_code=403, detail="重置密钥错误")

    admin = db.query(Admin).filter(Admin.username == body.username).first()
    if admin is None:
        raise HTTPException(status_code=404, detail="管理员不存在")

    admin.password_hash = hash_password(body.new_password)
    db.commit()
    return MessageResponse(message="密码重置成功")
