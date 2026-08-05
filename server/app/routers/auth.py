"""认证相关路由：微信登录、获取当前用户"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.user import User
from app.schemas.schemas import LoginRequest, TokenResponse, UserResponse
from app.services.wx_service import code_to_openid

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """微信登录：接收 wx.login code，返回 JWT

    - 首次登录自动创建用户
    - 已注册用户直接返回 token
    """
    # 换取 openid
    try:
        openid = await code_to_openid(body.code)
    except ValueError as e:
        logger.warning("微信登录失败：无效 code，原因={}", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    except RuntimeError as e:
        logger.error("微信登录失败：code2session 调用异常，原因={}", e)
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
    logger.info("微信登录成功", openid=openid, is_new=is_new)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
