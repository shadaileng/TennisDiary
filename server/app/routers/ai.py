"""AI 评分代理路由（POST /api/ai/analyze）"""

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.schemas import AnalyzeRequest
from app.services import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/analyze", response_model=ApiResponse[dict])
async def analyze(req: AnalyzeRequest, current_user: User = Depends(get_current_user)):
    """AI 六维评分代理：Key 存服务端，无 Key / 调用失败走本地降级（HTTP 200）"""
    if not settings.AI_API_KEY:
        logger.warning(f"AI 未配置 Key，返回本地降级报告 kind={req.kind}")
        return ApiResponse(data=ai_service.build_local_report(req.kind))

    try:
        report = await ai_service.analyze_swing(req.frames, req.kind, req.mode)
        return ApiResponse(data=report)
    except Exception as exc:  # noqa: BLE001 - 统一降级，不向上抛 5xx
        logger.error(f"AI 分析失败，降级: {exc}")
        return ApiResponse(data=ai_service.build_local_report(req.kind))
