"""头像上传相关路由"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User

router = APIRouter(prefix="/api/upload", tags=["upload"])

# 允许的图片扩展名 -> 子目录
_ALLOWED_EXT = {".jpg": "images", ".jpeg": "images", ".png": "images", ".webp": "images"}
_AVATAR_DIR = "avatars"


def _resolve_avatar_abs_path(rel_path: str) -> str | None:
    """将头像相对路径解析为 UPLOAD_DIR 内的绝对路径，越界返回 None"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    candidate = os.path.normpath(os.path.join(upload_dir, rel_path))
    if candidate != upload_dir and not candidate.startswith(upload_dir + os.sep):
        return None
    return candidate


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传当前用户头像，返回可用于 <image> 展示的相对 URL

    - 仅接受 jpg/jpeg/png/webp 图片
    - 存储到 UPLOAD_DIR/avatars/<user_id>/<uuid>.<ext>
    - 返回 {"url": "avatars/<user_id>/<uuid>.<ext>"}
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        logger.warning("头像上传拒绝：非法扩展名", user_id=current_user.id, ext=ext)
        detail = "仅支持 jpg/jpeg/png/webp 图片"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    rel_dir = os.path.join(_AVATAR_DIR, str(current_user.id))
    abs_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, rel_dir))
    os.makedirs(abs_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    rel_path = os.path.join(rel_dir, filename)
    abs_path = os.path.join(abs_dir, filename)

    with open(abs_path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            out.write(chunk)

    logger.info("头像上传成功", user_id=current_user.id, path=rel_path)
    return {"url": rel_path.replace(os.sep, "/")}


@router.get("/avatar/{user_id}/{filename}")
def download_avatar(user_id: int, filename: str):
    """下载头像（公开访问，无需鉴权；URL 含 user_id + UUID 不可猜测）"""
    rel_path = os.path.join(_AVATAR_DIR, str(user_id), filename)
    abs_path = _resolve_avatar_abs_path(rel_path)
    if abs_path is None or not os.path.isfile(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return FileResponse(abs_path)
