"""文件下载相关路由：按相对路径下载当前用户拥有的文件"""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.models.gear import Gear
from app.models.user import User

router = APIRouter(prefix="/api/files", tags=["files"])

# 扩展名 -> content-type 映射（仅常用类型，其余回退 octet-stream）
_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".pdf": "application/pdf",
}


def _resolve_safe_path(filename: str) -> str | None:
    """将 filename 解析为 UPLOAD_DIR 内的绝对路径，若越界返回 None"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    # normpath 处理 ../ 与多余分隔符；要求结果仍位于 upload_dir 内
    candidate = os.path.normpath(os.path.join(upload_dir, filename))
    if candidate != upload_dir and not candidate.startswith(upload_dir + os.sep):
        return None
    return candidate


def _is_file_owned(db: Session, user: User, rel_path: str) -> bool:
    """判断该相对路径是否被当前用户拥有的 Gear 引用"""
    gear = db.query(Gear).filter(Gear.user_id == user.id, Gear.photo == rel_path).first()
    return gear is not None


@router.get("/{filename:path}")
def download_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载当前用户拥有的文件，完成路径穿越防护与归属校验"""
    abs_path = _resolve_safe_path(filename)
    if abs_path is None:
        logger.warning("文件下载路径穿越被拒", user_id=current_user.id, filename=filename)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    if not _is_file_owned(db, current_user, filename):
        logger.warning("文件下载越权被拒", user_id=current_user.id, filename=filename)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    ext = os.path.splitext(abs_path)[1].lower()
    media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")
    logger.info("文件下载成功", user_id=current_user.id, filename=filename)
    return FileResponse(abs_path, media_type=media_type)
