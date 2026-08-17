"""用户端媒体服务路由（GET /api/media/{path}）

供小程序 <image>/<video> 加载视频 / 帧 / 骨架文件。
小程序媒体组件无法携带自定义请求头，鉴权同时支持 X-Auth-Token 头与 ?token= 查询参数
（见 app.core.auth.get_current_user_media）。
"""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.auth import get_current_user_media
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User

log = get_logger("user")

router = APIRouter(prefix="/api/media", tags=["media"])

# 复用 files.py 的媒体类型表（jpeg/png/gif/webp/mp4/mov/pdf）
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
    """解析并校验媒体相对路径：必须在 UPLOAD_DIR 内，穿越/越界返回 None"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    candidate = os.path.normpath(os.path.join(upload_dir, filename))
    if candidate != upload_dir and candidate.startswith(upload_dir + os.sep):
        return candidate
    return None


def _owned(filename: str, user: User) -> bool:
    """归属校验：仅允许访问 videos/{current_user_id}/ 下的文件"""
    parts = filename.split("/")
    return len(parts) >= 3 and parts[0] == "videos" and parts[1] == str(user.id)


@router.get("/{filename:path}", response_class=FileResponse)
def serve_media(
    filename: str,
    current_user: User = Depends(get_current_user_media),
):
    """服务当前用户上传的视频 / 帧 / 骨架文件；越权 403，越界/不存在 404"""
    abs_path = _resolve_safe_path(filename)
    if abs_path is None:
        log.warning("媒体路径穿越被拒", user_id=current_user.id, filename=filename)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    if not _owned(filename, current_user):
        log.warning("媒体访问越权被拒", user_id=current_user.id, filename=filename)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该文件")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    ext = os.path.splitext(filename)[1].lower()
    media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")
    return FileResponse(abs_path, media_type=media_type)
