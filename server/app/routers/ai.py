"""AI 评分代理路由（POST /api/ai/analyze、POST /api/ai/caption）"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.decorators.audit import audit
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.schemas import AnalyzeRequest, CaptionRequest, CaptionResponse
from app.services import ai_service
from app.services.config_service import get_ai_config

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _persist_report(db: Session, analysis_id: int | None, report: dict) -> None:
    """118 步骤3：列定向更新 Analysis 的评分列（与上传/姿态并发提交不互相覆盖）"""
    if analysis_id is None:
        return
    try:
        stmt = (
            sa_update(Analysis)
            .where(Analysis.id == analysis_id)
            .values(
                report=json.dumps(report, ensure_ascii=False),
                score=report.get("score") or 0,
                ntrp=report.get("ntrp"),
                summary=report.get("summary") or "",
            )
        )
        db.execute(stmt)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 落库失败仅记录，不影响评分返回
        logger.error("AI 评分结果落库失败 analysis_id=%s: %s", analysis_id, exc, exc_info=True)
        db.rollback()


@router.post("/analyze", response_model=ApiResponse[dict])
@audit(action="ANALYZE", resource_type="ai")
async def analyze(
    req: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 六维评分代理：Key 存服务端，无 Key / 调用失败走本地降级（HTTP 200）

    若携带 analysis_id（118 流水线步骤3）：评分后列定向更新同一分析记录，
    不取对象整体提交，避免与步骤2/4 并发互相覆盖（丢失更新）。
    """
    analysis_id = req.analysis_id
    if analysis_id is not None:
        owned = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id)
            .first()
        )
        if owned is None:
            return ApiResponse(code=10001, message="分析记录不存在或越权", success=False, data=None)

    ai_config = get_ai_config(db)
    if not ai_config.api_key:
        logger.warning("AI 未配置 Key，返回本地降级报告 kind=%s", req.kind)
        report = ai_service.build_local_report(req.kind)
        _persist_report(db, analysis_id, report)
        return ApiResponse(data=report)

    try:
        report = await ai_service.analyze_swing(
            req.frames, req.kind, req.mode, ai_config, frame_urls=req.frame_urls
        )
        _persist_report(db, analysis_id, report)
        return ApiResponse(data=report)
    except Exception as exc:  # noqa: BLE001 - 统一降级，不向上抛 5xx
        logger.error("AI 分析失败，降级: %s", exc, exc_info=True)
        report = ai_service.build_local_report(req.kind)
        _persist_report(db, analysis_id, report)
        return ApiResponse(data=report)


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
