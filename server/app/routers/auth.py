"""认证相关路由：微信登录、获取当前用户"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.schemas import (
    LoginRequest,
    LoginResponse,
    UserResponse,
    UserUpdate,
    UserUpdateResponse,
)
from app.services.wx_service import code_to_openid

log = get_logger("user")

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[LoginResponse])
@audit(action="LOGIN", resource_type="auth")
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """微信登录：接收 wx.login code，返回 JWT 与用户信息

    - 首次登录自动创建用户
    - 已注册用户直接返回 token 与用户
    """
    # 换取 openid
    try:
        openid = await code_to_openid(body.code)
    except ValueError as e:
        log.warning("微信登录失败：无效 code，原因={}", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    except RuntimeError as e:
        log.error("微信登录失败：code2session 调用异常，原因={}", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e

    # 查找或创建用户
    user = db.query(User).filter(User.openid == openid).first()
    is_new = user is None
    if user is None:
        user = User(openid=openid)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 签发 JWT
    token = create_access_token(openid)
    log.info("微信登录成功", openid=openid, is_new=is_new)
    return ApiResponse(
        data=LoginResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
            is_new=is_new,
        )
    )


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return ApiResponse(data=UserResponse.model_validate(current_user))


@router.put("/me", response_model=ApiResponse[UserUpdateResponse])
@audit(action="UPDATE", resource_type="user_profile")
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户资料（昵称/头像），仅更新传入字段"""
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    log.info("用户资料更新", user_id=current_user.id)
    return ApiResponse(data=UserUpdateResponse(user=UserResponse.model_validate(current_user)))
