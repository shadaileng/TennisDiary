"""Admin 动态配置路由（/api/admin/config）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.decorators.audit import audit
from app.models.admin import Admin
from app.schemas.admin import ConfigUpdateRequest
from app.schemas.common import ApiResponse
from app.services import config_service

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"])


@router.get("", response_model=ApiResponse[dict])
def list_configs(
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """全量配置列表（分类 + 来源状态 + 掩码）"""
    return ApiResponse(data=config_service.list_config_items(db))


@router.put("/{key}", response_model=ApiResponse[dict])
@audit(action="UPDATE", resource_type="config", resource_id_key="key")
def update_config(
    key: str,
    req: ConfigUpdateRequest,
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """设置配置覆盖值（生效值 = DB 覆盖 > env 默认）"""
    return ApiResponse(data=config_service.set_config_value(db, key, req.value, admin_id=admin.id))


@router.delete("/{key}", response_model=ApiResponse[dict])
@audit(action="DELETE", resource_type="config", resource_id_key="key")
def delete_config(
    key: str,
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """删除覆盖值（恢复环境变量默认）"""
    return ApiResponse(data=config_service.delete_config_value(db, key))


@router.post("/reset", response_model=ApiResponse[dict])
@audit(action="UPDATE", resource_type="config")
def reset_configs(
    admin: Admin = Depends(require_permission("system:config")),
    db: Session = Depends(get_db),
):
    """全部恢复环境变量默认"""
    config_service.reset_all(db)
    return ApiResponse(data={"message": "已全部恢复默认"})
