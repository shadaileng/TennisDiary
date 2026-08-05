from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import settings
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()


def create_access_token(openid: str) -> str:
    """签发 JWT access token"""
    to_encode = {"sub": openid}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """解码 JWT，返回 openid"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        openid: str = payload.get("sub")
        if openid is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token")
        return openid
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT 获取当前用户"""
    openid = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.openid == openid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user
