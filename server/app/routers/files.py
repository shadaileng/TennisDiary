"""文件下载相关路由：按相对路径下载当前用户拥有的文件"""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.mime import EXTENSION_MIME
from app.models.user import User
from app.services import file_service

log = get_logger("user")

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{filename:path}")
def download_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载当前用户拥有的文件，完成路径穿越防护与归属校验"""
    abs_path = file_service.resolve(filename)
    if abs_path is None:
        log.warning("文件下载路径穿越被拒", user_id=current_user.id, filename=filename)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    if not file_service.owned_by(db, current_user.id, filename):
        log.warning("文件下载越权被拒", user_id=current_user.id, filename=filename)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    if not file_service.exists(filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    ext = os.path.splitext(abs_path)[1].lower()
    media_type = EXTENSION_MIME.get(ext, "application/octet-stream")
    log.info("文件下载成功", user_id=current_user.id, filename=filename)
    return FileResponse(abs_path, media_type=media_type)
