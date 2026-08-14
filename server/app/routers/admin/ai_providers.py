"""Admin AI 服务商管理路由（/api/admin/config/providers）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.admin import AiProviderRequest
from app.schemas.common import ApiResponse
from app.services import ai_provider_service

router = APIRouter(prefix="/api/admin/config/providers", tags=["admin-ai-providers"])


@router.get("", response_model=ApiResponse[dict])
def list_providers(
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """服务商列表（api_key 掩码 + is_selected 引用标记）"""
    return ApiResponse(data=ai_provider_service.list_providers(db))


@router.post("", response_model=ApiResponse[dict])
def create_provider(
    req: AiProviderRequest,
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """新增服务商"""
    return ApiResponse(
        data=ai_provider_service.create_provider(
            db,
            name=req.name,
            base_url=req.base_url,
            api_key=req.api_key,
            models=req.models,
            enabled=req.enabled,
            sort_order=req.sort_order,
        )
    )


@router.put("/{provider_id}", response_model=ApiResponse[dict])
def update_provider(
    provider_id: int,
    req: AiProviderRequest,
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """编辑服务商（api_key 留空 = 保持不变）"""
    return ApiResponse(
        data=ai_provider_service.update_provider(
            db,
            provider_id=provider_id,
            name=req.name,
            base_url=req.base_url,
            api_key=req.api_key,
            models=req.models,
            enabled=req.enabled,
            sort_order=req.sort_order,
        )
    )


@router.delete("/{provider_id}", response_model=ApiResponse[dict])
def delete_provider(
    provider_id: int,
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """删除服务商（被 ai.provider 引用时 409）"""
    return ApiResponse(data=ai_provider_service.delete_provider(db, provider_id))
