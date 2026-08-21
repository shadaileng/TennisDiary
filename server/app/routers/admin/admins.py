"""管理员管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.decorators.audit import audit
from app.models.admin import Admin
from app.models.role import Role
from app.schemas.admin import (
    AdminCreateRequest,
    AdminResetPasswordRequest,
    AdminResponse,
    AdminUpdateRequest,
    RoleResponse,
)
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/admins", tags=["admin-admins"])


def _admin_to_response(admin: Admin) -> AdminResponse:
    """Admin转AdminResponse"""
    role_resp = RoleResponse.from_orm(admin.role) if admin.role else None
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        nickname=admin.nickname or "",
        role_id=admin.role_id,
        role=role_resp,
        is_active=admin.is_active,
        last_login=admin.last_login,
        created_at=admin.created_at,
    )


@router.get("", response_model=ApiResponse[PaginatedData[AdminResponse]])
def list_admins(
    offset: int = 0,
    limit: int = 20,
    admin: Admin = Depends(require_permission("admins:list")),
    db: Session = Depends(get_db),
):
    """管理员列表（分页）"""
    total = db.query(Admin).count()
    admins = db.query(Admin).offset(offset).limit(limit).all()
    items = [_admin_to_response(a) for a in admins]
    return ApiResponse(
        data=PaginatedData(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.post("", response_model=ApiResponse[AdminResponse])
@audit(action="CREATE", resource_type="admin")
def create_admin(
    body: AdminCreateRequest,
    admin: Admin = Depends(require_permission("admins:create")),
    db: Session = Depends(get_db),
):
    """创建管理员"""
    # 检查用户名唯一性
    existing = db.query(Admin).filter(Admin.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查角色是否存在
    role = db.query(Role).filter(Role.id == body.role_id).first()
    if role is None:
        raise HTTPException(status_code=400, detail="角色不存在")

    new_admin = Admin(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        role_id=body.role_id,
        is_active=True,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return ApiResponse(data=_admin_to_response(new_admin))


@router.get("/{admin_id}", response_model=ApiResponse[AdminResponse])
def get_admin(
    admin_id: int,
    admin: Admin = Depends(require_permission("admins:view")),
    db: Session = Depends(get_db),
):
    """管理员详情"""
    target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if target_admin is None:
        raise HTTPException(status_code=404, detail="管理员不存在")
    return ApiResponse(data=_admin_to_response(target_admin))


@router.put("/{admin_id}", response_model=ApiResponse[AdminResponse])
@audit(action="UPDATE", resource_type="admin", resource_id_key="admin_id")
def update_admin(
    admin_id: int,
    body: AdminUpdateRequest,
    admin: Admin = Depends(require_permission("admins:edit")),
    db: Session = Depends(get_db),
):
    """编辑管理员"""
    target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if target_admin is None:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if body.nickname is not None:
        target_admin.nickname = body.nickname
    if body.role_id is not None:
        role = db.query(Role).filter(Role.id == body.role_id).first()
        if role is None:
            raise HTTPException(status_code=400, detail="角色不存在")
        target_admin.role_id = body.role_id
    if body.is_active is not None:
        # 不能禁用自己
        if target_admin.id == admin.id:
            raise HTTPException(status_code=400, detail="不能修改自己的状态")
        target_admin.is_active = body.is_active

    db.commit()
    db.refresh(target_admin)
    return ApiResponse(data=_admin_to_response(target_admin))


@router.put("/{admin_id}/password", response_model=ApiResponse[None])
@audit(action="UPDATE", resource_type="admin", resource_id_key="admin_id")
def reset_password(
    admin_id: int,
    body: AdminResetPasswordRequest,
    admin: Admin = Depends(require_permission("admins:reset_password")),
    db: Session = Depends(get_db),
):
    """重置管理员密码"""
    target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if target_admin is None:
        raise HTTPException(status_code=404, detail="管理员不存在")

    target_admin.password_hash = hash_password(body.new_password)
    db.commit()
    return ApiResponse(message="密码重置成功")


@router.put("/{admin_id}/status", response_model=ApiResponse[None])
@audit(action="UPDATE", resource_type="admin", resource_id_key="admin_id")
def toggle_status(
    admin_id: int,
    admin: Admin = Depends(require_permission("admins:edit")),
    db: Session = Depends(get_db),
):
    """启用/禁用管理员"""
    target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if target_admin is None:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 不能禁用自己
    if target_admin.id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态")

    target_admin.is_active = not target_admin.is_active
    db.commit()
    status_text = "启用" if target_admin.is_active else "禁用"
    return ApiResponse(message=f"已{status_text}")


@router.delete("/{admin_id}", response_model=ApiResponse[None])
@audit(action="DELETE", resource_type="admin", resource_id_key="admin_id")
def delete_admin(
    admin_id: int,
    admin: Admin = Depends(require_permission("admins:delete")),
    db: Session = Depends(get_db),
):
    """删除管理员"""
    target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if target_admin is None:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 不能删除自己
    if target_admin.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db.delete(target_admin)
    db.commit()
    return ApiResponse(message="删除成功")
