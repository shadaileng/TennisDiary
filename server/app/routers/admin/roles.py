"""角色管理路由"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.core.permissions import PERMISSIONS
from app.models.admin import Admin
from app.models.role import Role
from app.schemas.admin import (
    MessageResponse,
    PermissionResponse,
    RoleCreateRequest,
    RoleListResponse,
    RoleResponse,
    RoleUpdateRequest,
)

router = APIRouter(prefix="/api/admin/roles", tags=["admin-roles"])


@router.get("", response_model=RoleListResponse)
def list_roles(
    admin: Admin = Depends(require_permission("roles:list")),
    db: Session = Depends(get_db),
):
    """角色列表"""
    roles = db.query(Role).all()
    items = [RoleResponse.from_orm(r) for r in roles]
    return RoleListResponse(items=items, total=len(items))


@router.post("", response_model=RoleResponse)
def create_role(
    body: RoleCreateRequest,
    admin: Admin = Depends(require_permission("roles:create")),
    db: Session = Depends(get_db),
):
    """创建角色"""
    # 检查编码唯一性
    existing = db.query(Role).filter(Role.code == body.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色编码已存在")

    # 校验权限码
    invalid_perms = [p for p in body.permissions if p not in PERMISSIONS]
    if invalid_perms:
        raise HTTPException(status_code=400, detail=f"无效的权限码: {invalid_perms}")

    role = Role(
        name=body.name,
        code=body.code,
        description=body.description,
        permissions=json.dumps(body.permissions, ensure_ascii=False),
        is_system=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return RoleResponse.from_orm(role)


@router.get("/permissions", response_model=PermissionResponse)
def list_permissions(
    admin: Admin = Depends(require_permission("roles:list")),
):
    """获取所有可用权限"""
    return PermissionResponse(permissions=PERMISSIONS)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    admin: Admin = Depends(require_permission("roles:view")),
    db: Session = Depends(get_db),
):
    """角色详情"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return RoleResponse.from_orm(role)


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    body: RoleUpdateRequest,
    admin: Admin = Depends(require_permission("roles:edit")),
    db: Session = Depends(get_db),
):
    """编辑角色"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可修改")

    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.permissions is not None:
        invalid_perms = [p for p in body.permissions if p not in PERMISSIONS]
        if invalid_perms:
            raise HTTPException(status_code=400, detail=f"无效的权限码: {invalid_perms}")
        role.permissions = json.dumps(body.permissions, ensure_ascii=False)

    db.commit()
    db.refresh(role)
    return RoleResponse.from_orm(role)


@router.delete("/{role_id}", response_model=MessageResponse)
def delete_role(
    role_id: int,
    admin: Admin = Depends(require_permission("roles:delete")),
    db: Session = Depends(get_db),
):
    """删除角色"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")

    # 检查是否有管理员使用此角色
    from app.models.admin import Admin as AdminModel

    admin_count = db.query(AdminModel).filter(AdminModel.role_id == role_id).count()
    if admin_count > 0:
        raise HTTPException(status_code=400, detail=f"该角色下有 {admin_count} 个管理员，无法删除")

    db.delete(role)
    db.commit()
    return MessageResponse(message="删除成功")
