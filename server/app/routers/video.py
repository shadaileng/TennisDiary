"""视频上传与抽帧路由（POST /api/video/upload）"""

import json
import os
import time
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.analysis import Analysis
from app.models.analysis_video_info import AnalysisVideoInfo
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import file_service, video_service
from app.services.content_security import check_media_sync
from app.services.video_service import (
    FfmpegUnavailableError,
    InvalidCutError,
    VideoTooLongError,
)

log = get_logger("user")

router = APIRouter(prefix="/api/video", tags=["video"])

# 允许的视频扩展名
_ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}


def _is_video_file(filename: str, content_type: str | None) -> bool:
    """按扩展名与 content-type 判断是否视频"""
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in _ALLOWED_VIDEO_EXT or (content_type or "").startswith("video/")


@router.post("/upload", response_model=ApiResponse[dict])
@audit(action="UPLOAD", resource_type="video")
def upload_video(
    file: UploadFile = File(...),
    mode: Literal["single", "full"] = Form(default="single"),
    kind: str = Form(default="综合"),
    hit_time: float | None = Form(default=None),
    cuts: str | None = Form(default=None),
    analysis_id: int | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传视频并抽帧：落盘 UPLOAD_DIR/videos/{user_id}/，ffmpeg 抽帧返回 base64 帧列表

    - mode=single：≤15s，7 帧（相对击球瞬间采样）；mode=full：≤90s，8 帧（均匀采样）
    - cuts（JSON 数组 `[{start,end},…]`，可选）：先由 ffmpeg 裁剪拼接后再抽帧，
      hit_time 为拼接后相对时间；返回 segments + trimmed 标志
    - 返回 frames（base64 dataURL，按时间顺序）+ duration + thumbnail + hit_time + mirage
    """
    if not _is_video_file(file.filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持视频文件（mp4/mov/m4v/webm）"
        )

    ext = os.path.splitext(file.filename or "")[1].lower() or ".mp4"
    original_name = file.filename or ""

    # 读取文件内容（文件名/落盘/登记全部由 file_service 门面按 MD5 统一处理）
    content = file.file.read()

    try:
        file_record, is_mirage = file_service.register(
            db=db,
            user_id=current_user.id,
            content=content,
            category="video",
            original_name=original_name,
            ext=ext,
        )
        db.commit()
    except Exception as exc:
        log.error("视频文件写入失败: user_id=%s error=%s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件写入失败，请稍后重试",
        ) from exc

    abs_path = file_service.abs_of(file_record.rel_path)
    rel_video = file_record.rel_path

    actual_size = file_service.size_of(rel_video)
    if actual_size == 0:
        file_service.soft_delete(db, file_record.id)
        db.commit()
        file_service.unlink(rel_video)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空，请重新选择视频"
        )

    log.info("视频上传完成: path=%s size=%s mirage=%s", rel_video, actual_size, is_mirage)

    # 解析裁剪参数
    parsed_cuts: list[dict] | None = None
    if cuts:
        try:
            parsed_cuts = json.loads(cuts)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="裁剪片段参数格式错误"
            ) from exc

    def _discard_upload() -> None:
        """上传后处理失败：回收刚登记的文件（秒传复用的共享文件不删）"""
        if is_mirage:
            return
        file_service.soft_delete(db, file_record.id)
        db.commit()
        file_service.unlink(rel_video)

    try:
        result = video_service.process_video(abs_path, mode, hit_time, cuts=parsed_cuts)
    except VideoTooLongError as exc:
        _discard_upload()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidCutError as exc:
        _discard_upload()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FfmpegUnavailableError as exc:
        _discard_upload()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务器未配置 ffmpeg，无法抽帧",
        ) from exc
    except Exception as exc:
        _discard_upload()
        log.error(f"视频处理失败: msg={exc!s} exc_type={type(exc).__name__} path={abs_path}")
        detail = str(exc) if isinstance(exc, ValueError) else "视频处理失败，请检查文件格式"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    result["kind"] = kind
    result["mirage"] = is_mirage

    # 裁切后 working != abs_path；登记为受管文件后 video_url 指向受管路径
    working_path = result.get("working_path") or abs_path
    playback_record, _ = file_service.register(
        db=db,
        user_id=current_user.id,
        src_path=working_path,
        category="video_playback",
        original_name=f"{os.path.basename(working_path)}_playback",
        ext=os.path.splitext(working_path)[1] or ".mp4",
    )
    rel_video_result = playback_record.rel_path
    result["video_url"] = rel_video_result

    # 抽帧中间产物登记为受管文件（{md5}.jpg）
    frame_records = file_service.register_batch(
        db,
        current_user.id,
        [
            file_service.FileDraft(
                src_path=frame_path,
                ext=os.path.splitext(frame_path)[1] or ".jpg",
                upload_source="video_frame",
                original_name=os.path.basename(frame_path),
            )
            for frame_path in result.get("frame_paths", [])
        ],
    )
    db.commit()
    result["frame_urls"] = [record.rel_path for record in frame_records]

    log.info(
        f"视频处理完成: duration={result.get('duration', 0):.2f}s "
        f"frames={len(result.get('frame_urls', []))} "
        f"trimmed={result.get('trimmed', False)} "
        f"working={rel_video_result} mirage={is_mirage}"
    )

    # 若携带 analysis_id：验证归属 + 登记衍生文件 + 列定向更新 Analysis
    if analysis_id is not None:
        existing = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id)
            .first()
        )
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")

        # 原片 / 播放短片 / 抽帧统一绑定到该分析记录（ref_count 自动 +1）
        for record in [file_record, playback_record, *frame_records]:
            file_service.bind(db, current_user.id, record.rel_path, "analysis", analysis_id)

        # 登记 analysis_video_info
        cut_info = {
            "segments": result.get("segments"),
            "hit_time": result.get("hit_time"),
            "mode": mode,
            "kind": kind,
        }
        derivatives = [
            {
                "kind": "playback",
                "rel_path": playback_record.rel_path,
                "file_id": playback_record.id,
                "mime_type": playback_record.mime_type,
                "size_bytes": playback_record.size_bytes,
            }
        ]
        derivatives.extend(
            {
                "kind": "frame",
                "rel_path": record.rel_path,
                "file_id": record.id,
                "mime_type": record.mime_type or "image/jpeg",
                "size_bytes": record.size_bytes,
            }
            for record in frame_records
        )

        analysis_video_info = AnalysisVideoInfo(
            user_id=current_user.id,
            analysis_id=analysis_id,
            source_file_id=file_record.id,
            playback_file_id=playback_record.id if playback_record else None,
            cut_info=json.dumps(cut_info, ensure_ascii=False),
            derivatives=json.dumps(derivatives, ensure_ascii=False),
            created_at=time.time(),
        )
        db.add(analysis_video_info)
        # 列定向更新：仅写 video_url，避免并发覆盖
        db.execute(
            sa_update(Analysis).where(Analysis.id == analysis_id).values(video_url=rel_video_result)
        )
        db.commit()

    # 异步内容安全检查（不阻断上传流程）
    try:
        media_result = check_media_sync(abs_path, str(current_user.id), media_type=3)
        if media_result.get("errcode"):
            log.warning(
                "视频内容安全检查 API 返回错误",
                user_id=current_user.id,
                errcode=media_result["errcode"],
            )
        else:
            log.info(
                "视频内容安全检查已提交",
                user_id=current_user.id,
                trace_id=media_result.get("trace_id", ""),
            )
    except Exception as exc:
        log.error("视频安全检查异常: %s", exc, exc_info=True)

    log.info(
        "视频抽帧完成",
        user_id=current_user.id,
        frames=len(result["frames"]),
        duration=result["duration"],
    )
    return ApiResponse(data=result)
