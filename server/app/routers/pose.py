"""姿态推理路由（POST /api/pose/analyze, POST /api/pose/video）"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.analysis import Analysis
from app.models.analysis_video_info import AnalysisVideoInfo
from app.models.file import File
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import file_service, pose_service
from app.services.pose_service import PoseUnavailableError

log = get_logger("user")

router = APIRouter(prefix="/api/pose", tags=["pose"])


class PoseAnalyzeRequest(BaseModel):
    """姿态推理请求：优先使用 frame_urls（后端读文件），兼容 frames（前端直传）"""

    frames: list[str] | None = Field(
        default=None, description="关键帧 base64/dataURL 数组（兼容旧版）"
    )
    frame_urls: list[str] | None = Field(
        default=None, description="帧文件相对路径数组（推荐，后端读文件）"
    )
    video_url: str | None = Field(
        default=None, description="源视频相对 UPLOAD_DIR 的路径；save_skeleton 时用于落盘骨架帧"
    )
    save_skeleton: bool = Field(
        default=False, description="是否绘制骨架帧并落盘（skeleton_frames/video/thumb）"
    )
    duration: float | None = Field(default=None, description="视频时长（秒），骨架动画 fps 推算用")
    frame_rate: float | None = Field(default=None, description="视频帧率（fps），用于骨架动画编码")
    full_frames: bool | None = Field(
        default=None,
        description="是否逐帧生成骨架视频（null=自动判断，true=强制逐帧，false=强制抽样）",
    )
    analysis_id: int | None = Field(
        default=None, description="关联分析记录 ID（118 流水线：分步更新同一行）"
    )


class PoseVideoRequest(BaseModel):
    """从视频文件直接生成骨架视频（帧数与原视频一致）"""

    video_url: str = Field(description="源视频相对 UPLOAD_DIR 的路径")
    frame_rate: float | None = Field(default=None, description="视频帧率（fps），用于骨架动画编码")


@router.post("/analyze", response_model=ApiResponse[dict])
@audit(action="ANALYZE", resource_type="pose")
def analyze(
    req: PoseAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """MediaPipe 姿态推理：逐帧输出 33 关键点 + 首个可测帧的三角度测量

    - save_skeleton=true 时绘制骨架帧落盘并尝试编码骨架动画 mp4（video_url 必须合法且存在）
    - 模型缺失 / mediapipe 未安装 → 503（提示清晰）
    - 无人检测 → 200 + detected=false + metrics=null（不报错，AI 侧走本地降级）
    - 帧数据非法 / video_url 越界 → 400
    """
    if not pose_service.is_available():
        log.warning("姿态推理服务不可用：mediapipe 或模型缺失")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="姿态推理服务不可用：模型缺失或 mediapipe 未安装",
        )

    try:
        result = pose_service.analyze_frames(
            req.frames,
            video_url=req.video_url,
            save_skeleton=req.save_skeleton,
            duration=req.duration,
            frame_rate=req.frame_rate,
            full_frames=req.full_frames,
            frame_urls=req.frame_urls,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PoseUnavailableError as exc:
        log.error("姿态推理失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        log.error("姿态推理异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="姿态推理服务异常，请稍后重试",
        ) from exc

    log.info(
        "姿态推理完成",
        user_id=current_user.id,
        frames=len(result["frames"]),
        detected=result["detected"],
        save_skeleton=req.save_skeleton,
    )

    # 118 步骤4：携带 analysis_id 时，登记骨架文件 + 列定向更新 Analysis + 追加 derivatives
    if req.analysis_id is not None:
        existing = (
            db.query(Analysis)
            .filter(Analysis.id == req.analysis_id, Analysis.user_id == current_user.id)
            .first()
        )
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在或越权"
            )
        _persist_pose(db, current_user.id, req.analysis_id, result)

    return ApiResponse(data=result)


def _persist_pose(db: Session, user_id: int, analysis_id: int, result: dict) -> None:
    """118 步骤4：登记骨架衍生文件、列定向更新 pose/thumb、追加 analysis_video_info.derivatives"""
    skeleton_paths: list[str] = []
    for p in result.get("skeleton_frames") or []:
        if p:
            skeleton_paths.append(p)
    if result.get("skeleton_video_url"):
        skeleton_paths.append(result["skeleton_video_url"])
    if result.get("skeleton_thumb"):
        skeleton_paths.append(result["skeleton_thumb"])

    if skeleton_paths:
        file_service.register_ai_files(
            db=db,
            user_id=user_id,
            paths=skeleton_paths,
            business_type="analysis",
            business_id=analysis_id,
        )
        db.flush()

    # 列定向更新：仅写 pose / thumb，避免并发覆盖步骤2/3 已填列
    stmt = (
        sa_update(Analysis)
        .where(Analysis.id == analysis_id)
        .values(
            pose=json.dumps(result, ensure_ascii=False),
            thumb=result.get("skeleton_thumb"),
        )
    )
    db.execute(stmt)

    # 追加 derivatives（步骤4 是最后写入方，先查后并）
    info = db.query(AnalysisVideoInfo).filter(AnalysisVideoInfo.analysis_id == analysis_id).first()
    if info is not None:
        derivatives = json.loads(info.derivatives) if info.derivatives else []
        seen = {(d.get("kind"), d.get("rel_path")) for d in derivatives}
        for rel in skeleton_paths:
            if ("skeleton", rel) in seen:
                continue
            rec = (
                db.query(File)
                .filter(
                    file_service.File.user_id == user_id,
                    file_service.File.rel_path == rel,
                    file_service.File.business_type == "analysis",
                    file_service.File.business_id == analysis_id,
                )
                .first()
            )
            abs_path = file_service.rel_path_to_abs(rel)
            derivatives.append(
                {
                    "kind": "skeleton",
                    "rel_path": rel,
                    "file_id": rec.id if rec else 0,
                    "mime_type": rec.mime_type if rec else "",
                    "size_bytes": file_service.get_file_size(abs_path),
                }
            )
        info.derivatives = json.dumps(derivatives, ensure_ascii=False)

    db.commit()


@router.post("/video", response_model=ApiResponse[dict])
@audit(action="ANALYZE_VIDEO", resource_type="pose")
def analyze_video(req: PoseVideoRequest, current_user: User = Depends(get_current_user)):
    """从视频文件逐帧读取并生成骨架视频（帧数与原视频一致）

    - video_url: 视频相对 UPLOAD_DIR 的路径（如 videos/1/xxx_seg0.mp4）
    - 返回: frames（每帧关键点）、metrics（角度测量）、skeleton_video_url（骨架视频）
    - 适用于需要骨架视频帧数与原视频同步的场景
    """
    if not pose_service.is_available():
        log.warning("姿态推理服务不可用：mediapipe 或模型缺失")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="姿态推理服务不可用：模型缺失或 mediapipe 未安装",
        )

    # 使用 file_service 解析视频路径
    video_path = file_service.resolve_safe_path(req.video_url)
    if video_path is None or not file_service.file_exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_url 无效或文件不存在",
        )

    try:
        result = pose_service.analyze_video_file(
            video_path,
            video_url=req.video_url,
            frame_rate=req.frame_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PoseUnavailableError as exc:
        log.error("姿态推理失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        log.error("姿态推理异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="姿态推理服务异常，请稍后重试",
        ) from exc

    log.info(
        "视频姿态推理完成",
        user_id=current_user.id,
        frames=len(result["frames"]),
        detected=result["detected"],
        video_url=req.video_url,
    )
    return ApiResponse(data=result)
