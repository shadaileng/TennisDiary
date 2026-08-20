"""视频上传与抽帧路由（POST /api/video/upload）"""

import json
import os
import shutil
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import video_service
from app.services.video_service import (
    FfmpegUnavailableError,
    InvalidCutError,
    VideoTooLongError,
)

log = get_logger("user")

router = APIRouter(prefix="/api/video", tags=["video"])

# 允许的视频扩展名
_ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}


def _safe_unlink(path: str) -> None:
    """删除失败文件；文件已不存在时忽略（避免 catch 内二次 unlink 抛错变 500）"""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


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
    cuts: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
):
    """上传视频并抽帧：落盘 UPLOAD_DIR/videos/{user_id}/，ffmpeg 抽帧返回 base64 帧列表

    - mode=single：≤15s，7 帧（相对击球瞬间采样）；mode=full：≤90s，8 帧（均匀采样）
    - cuts（JSON 数组 `[{start,end},…]`，可选）：先由 ffmpeg 裁剪拼接后再抽帧，
      hit_time 为拼接后相对时间；返回 segments + trimmed 标志
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
    written = 0
    try:
        with open(abs_path, "wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                written += len(chunk)
            out.flush()
            os.fsync(out.fileno())
    except Exception:
        os.makedirs(abs_dir, exist_ok=True)
        if os.path.isfile(abs_path):
            os.unlink(abs_path)
        raise

    actual_size = os.path.getsize(abs_path)
    log.info(f"视频上传完成: path={abs_path} written={written} actual={actual_size}")

    if actual_size == 0:
        os.unlink(abs_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空，请重新选择视频"
        )

    parsed_cuts: list[dict] | None = None
    if cuts:
        try:
            parsed_cuts = json.loads(cuts)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="裁剪片段参数格式错误"
            ) from exc

    try:
        result = video_service.process_video(abs_path, mode, hit_time, cuts=parsed_cuts)
    except VideoTooLongError as exc:
        _safe_unlink(abs_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidCutError as exc:
        _safe_unlink(abs_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FfmpegUnavailableError as exc:
        _safe_unlink(abs_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务器未配置 ffmpeg，无法抽帧",
        ) from exc
    except Exception as exc:
        exists = os.path.isfile(abs_path)
        size = os.path.getsize(abs_path) if exists else -1
        kept = ""
        if isinstance(exc, ValueError):
            # 保留失败副本便于排查上传字节问题（定位后清理）
            try:
                keep_path = os.path.join(abs_dir, f"_debug_{uuid.uuid4().hex}{ext}")
                shutil.copy2(abs_path, keep_path)
                kept = keep_path
            except OSError as copy_err:
                log.warning(f"保留失败副本失败: {copy_err} path={abs_path} exists={exists} size={size}")
                kept = ""
        log.error(
            f"视频处理失败: {exc} exc_type={type(exc).__name__} "
            f"path={abs_path} exists={exists} size={size} kept={kept}"
        )
        _safe_unlink(abs_path)
        # ValueError 类（如"无法解析视频时长"）消息面向用户，直接透出便于定位问题
        detail = str(exc) if isinstance(exc, ValueError) else "视频处理失败，请检查文件格式"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
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
