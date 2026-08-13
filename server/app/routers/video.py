"""视频上传与抽帧路由（POST /api/video/upload）"""

import os
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import video_service
from app.services.video_service import FfmpegUnavailableError, VideoTooLongError

log = get_logger("user")

router = APIRouter(prefix="/api/video", tags=["video"])

# 允许的视频扩展名
_ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}


def _is_video_file(filename: str, content_type: str | None) -> bool:
    """按扩展名与 content-type 判断是否视频"""
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in _ALLOWED_VIDEO_EXT or (content_type or "").startswith("video/")


@router.post("/upload", response_model=ApiResponse[dict])
def upload_video(
    file: UploadFile = File(...),
    mode: Literal["single", "full"] = Form(default="single"),
    kind: str = Form(default="综合"),
    hit_time: float | None = Form(default=None),
    current_user: User = Depends(get_current_user),
):
    """上传视频并抽帧：落盘 UPLOAD_DIR/videos/{user_id}/，ffmpeg 抽帧返回 base64 帧列表

    - mode=single：≤15s，7 帧（相对击球瞬间采样）；mode=full：≤90s，8 帧（均匀采样）
    - 返回 frames（base64 dataURL，按时间顺序）+ duration + thumbnail + hit_time
    """
    if not _is_video_file(file.filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持视频文件（mp4/mov/m4v/webm）"
        )

    ext = os.path.splitext(file.filename or "")[1].lower() or ".mp4"
    rel_dir = os.path.join("videos", str(current_user.id))
    abs_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, rel_dir))
    os.makedirs(abs_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(abs_dir, filename)

    # 分块写入，避免大视频占用内存
    try:
        with open(abs_path, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
    except Exception:
        os.makedirs(abs_dir, exist_ok=True)
        if os.path.isfile(abs_path):
            os.unlink(abs_path)
        raise

    actual_size = os.path.getsize(abs_path)

    if actual_size == 0:
        os.unlink(abs_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空，请重新选择视频"
        )

    try:
        result = video_service.process_video(abs_path, mode, hit_time)
    except VideoTooLongError as exc:
        os.unlink(abs_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FfmpegUnavailableError as exc:
        os.unlink(abs_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务器未配置 ffmpeg，无法抽帧",
        ) from exc
    except Exception as exc:
        log.error("视频处理失败", path=abs_path, error=str(exc))
        os.unlink(abs_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="视频处理失败，请检查文件格式"
        ) from exc

    result["kind"] = kind
    rel_video = os.path.relpath(abs_path, settings.UPLOAD_DIR).replace(os.sep, "/")
    result["video_url"] = rel_video
    log.info(
        "视频抽帧完成",
        user_id=current_user.id,
        frames=len(result["frames"]),
        duration=result["duration"],
    )
    return ApiResponse(data=result)
