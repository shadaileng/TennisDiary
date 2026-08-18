"""姿态推理路由（POST /api/pose/analyze）"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import pose_service
from app.services.pose_service import PoseUnavailableError

log = get_logger("user")

router = APIRouter(prefix="/api/pose", tags=["pose"])


class PoseAnalyzeRequest(BaseModel):
    """姿态推理请求：frames 为按时间顺序抽取的关键帧（base64/dataURL）"""

    frames: list[str] = Field(min_length=1, description="关键帧 base64/dataURL 数组")
    video_url: str | None = Field(
        default=None, description="源视频相对 UPLOAD_DIR 的路径；save_skeleton 时用于落盘骨架帧"
    )
    save_skeleton: bool = Field(
        default=False, description="是否绘制骨架帧并落盘（skeleton_frames/video/thumb）"
    )
    duration: float | None = Field(default=None, description="视频时长（秒），骨架动画 fps 推算用")
    frame_rate: float | None = Field(default=None, description="视频帧率（fps），用于骨架动画编码")


@router.post("/analyze", response_model=ApiResponse[dict])
def analyze(req: PoseAnalyzeRequest, current_user: User = Depends(get_current_user)):
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PoseUnavailableError as exc:
        log.error(f"姿态推理失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        log.error(f"姿态推理异常: {exc}", exc_info=True)
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
    return ApiResponse(data=result)
