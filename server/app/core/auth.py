"""JWT签发与鉴权核心"""

import json
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# 自定义鉴权头（魔搭网关占用 Authorization，需绕开）
AUTH_HEADER = "X-Auth-Token"
auth_scheme = APIKeyHeader(name=AUTH_HEADER, auto_error=False)

# 管理员JWT配置（独立密钥）
ADMIN_JWT_SECRET = "admin-secret-change-in-production"
ADMIN_JWT_ALGORITHM = "HS256"
ADMIN_JWT_EXPIRATION_HOURS = 24


def get_token_from_header(
    x_auth_token: str | None = Depends(auth_scheme),
) -> str:
    """从请求头读取 JWT，统一使用 X-Auth-Token"""
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return x_auth_token


def create_access_token(openid: str) -> str:
    """签发普通用户JWT"""
    to_encode = {"sub": openid, "type": "user"}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """解码普通用户JWT，返回openid"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "user":
            raise HTTPException(status_code=401, detail="无效的 token")
        openid = payload.get("sub")
        if openid is None:
            raise HTTPException(status_code=401, detail="无效的 token")
        return openid
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的 token") from None


def create_admin_access_token(admin_id: int) -> str:
    """签发管理员JWT"""
    expire = datetime.utcnow() + timedelta(hours=ADMIN_JWT_EXPIRATION_HOURS)
    to_encode = {
        "sub": f"admin:{admin_id}",
        "type": "admin",
        "exp": expire,
    }
    return jwt.encode(to_encode, ADMIN_JWT_SECRET, algorithm=ADMIN_JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db),
):
    """从JWT获取当前用户"""
    from app.models.user import User

    openid = decode_access_token(token)
    user = db.query(User).filter(User.openid == openid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_current_user_media(
    x_auth_token: str | None = Depends(auth_scheme),
    token: str | None = Query(default=None, description="媒体组件无法带头，query 回退传 token"),
    db: Session = Depends(get_db),
):
    """媒体访问鉴权：优先 X-Auth-Token 头，缺失时回退 ?token= 查询参数"""
    from app.models.user import User

    jwt_token = x_auth_token or token
    if not jwt_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    openid = decode_access_token(jwt_token)
    user = db.query(User).filter(User.openid == openid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_current_admin(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db),
):
    """从JWT获取当前管理员"""
    from app.models.admin import Admin

    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ADMIN_JWT_ALGORITHM])
        if payload.get("type") != "admin":
            raise HTTPException(status_code=403, detail="需要管理员权限")
        sub = payload.get("sub")
        if sub is None or not sub.startswith("admin:"):
            raise HTTPException(status_code=401, detail="无效的token")
        admin_id = int(sub.split(":")[1])
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if admin is None or not admin.is_active:
            raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
        return admin
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的token") from None


def require_permission(permission: str):
    """权限校验依赖

    用法：
        @router.get("/users")
        def list_users(admin: Admin = Depends(require_permission("users:list"))):
            ...
    """

    def permission_checker(
        admin=Depends(get_current_admin),
        db: Session = Depends(get_db),
    ):
        from app.models.role import Role

        role = db.query(Role).filter(Role.id == admin.role_id).first()
        if role is None:
            raise HTTPException(status_code=403, detail="角色不存在")

        permissions = json.loads(role.permissions) if role.permissions else []
        if permission not in permissions and role.code != "superadmin":
            raise HTTPException(status_code=403, detail="权限不足")

        return admin

    return permission_checker
