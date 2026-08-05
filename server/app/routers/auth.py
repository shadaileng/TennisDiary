"""认证相关路由：微信登录、获取当前用户"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import create_access_token, get_current_user
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    # 查找或创建用户
    user = db.query(User).filter(User.openid == openid).first()
    if user is None:
        user = User(openid=openid)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 签发 JWT
    token = create_access_token(openid)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
