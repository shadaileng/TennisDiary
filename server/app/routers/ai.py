"""AI 评分代理路由（POST /api/ai/analyze、POST /api/ai/caption）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.decorators.audit import audit
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.schemas import AnalyzeRequest, CaptionRequest, CaptionResponse
from app.services import ai_service
from app.services.config_service import get_ai_config

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/analyze", response_model=ApiResponse[dict])
@audit(action="ANALYZE", resource_type="ai")
async def analyze(
    req: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 六维评分代理：Key 存服务端，无 Key / 调用失败走本地降级（HTTP 200）"""
    ai_config = get_ai_config(db)
    if not ai_config.api_key:
        logger.warning(f"AI 未配置 Key，返回本地降级报告 kind={req.kind}")
        return ApiResponse(data=ai_service.build_local_report(req.kind))

    try:
        report = await ai_service.analyze_swing(req.frames, req.kind, req.mode, ai_config)
        return ApiResponse(data=report)
    except Exception as exc:  # noqa: BLE001 - 统一降级，不向上抛 5xx
        logger.error(f"AI 分析失败，降级: {exc}", exc_info=True)
        return ApiResponse(data=ai_service.build_local_report(req.kind))


@router.post("/caption", response_model=ApiResponse[CaptionResponse])
@audit(action="ANALYZE", resource_type="ai")
async def caption(
    req: CaptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 分享文案生成：按模板类型 + 当前用户查库，多风格；无 Key / 失败走本地模板降级"""
    context = ai_service.build_caption_context(db, current_user, req.template)
    ai_config = get_ai_config(db)
    if not ai_config.api_key:
        logger.warning(f"AI 未配置 Key，返回本地降级文案 template={req.template}")
        caption = ai_service.build_local_caption(req.template, context)
        return ApiResponse(data=CaptionResponse(caption=caption))

    try:
        text = await ai_service.generate_caption(
            req.template, req.style, context, ai_config, req.text
        )
        return ApiResponse(data=CaptionResponse(caption=text))
    except Exception as exc:  # noqa: BLE001 - 统一降级，不向上抛 5xx
        logger.error(f"AI 文案生成失败，降级: {exc}", exc_info=True)
        caption = ai_service.build_local_caption(req.template, context)
        return ApiResponse(data=CaptionResponse(caption=caption))
