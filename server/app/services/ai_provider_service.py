"""AI 服务商服务：手动维护 OpenAI 兼容 API 凭据列表（引用式直选）"""

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ai_provider import AiProvider
from app.services.config_service import mask_secret


def _build_provider_item(provider: AiProvider, is_selected: bool = False) -> dict[str, Any]:
    """构造单条服务商响应（api_key 掩码 + 是否被引用）"""
    return {
        "id": provider.id,
        "name": provider.name,
        "base_url": provider.base_url,
        "api_key": mask_secret(provider.api_key or ""),
        "models": list(provider.models),
        "default_model": provider.default_model,
        "enabled": bool(provider.enabled),
        "sort_order": provider.sort_order,
        "is_selected": is_selected,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
    }


def _validate_models(models: list[str]) -> list[str]:
    """模型列表校验：逐项 trim、去空后至少 1 项"""
    cleaned = [m.strip() for m in (models or [])]
    cleaned = [m for m in cleaned if m]
    if not cleaned:
        raise HTTPException(status_code=400, detail="models 至少需要一个模型")
    return cleaned


def _validate_base_url(base_url: str) -> str:
    if not (base_url.startswith(("http://", "https://"))):
        raise HTTPException(status_code=400, detail="base_url 必须是 http(s):// 开头的合法地址")
    return base_url


def _validate_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    query = db.query(AiProvider).filter(AiProvider.name == name)
    if exclude_id is not None:
        query = query.filter(AiProvider.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail=f"服务商名称已存在: {name}")


def list_providers(db: Session) -> dict[str, Any]:
    """全部服务商（按 sort_order/name 排序），含 is_selected 标记"""
    from app.services.config_service import get_config_value

    selected = get_config_value(db, "ai.provider") or "custom"
    rows = db.query(AiProvider).order_by(AiProvider.sort_order, AiProvider.id).all()
    return {"providers": [_build_provider_item(p, is_selected=(p.name == selected)) for p in rows]}


def create_provider(
    db: Session,
    name: str,
    base_url: str,
    api_key: str,
    models: list[str],
    enabled: bool = True,
    sort_order: int = 0,
) -> dict[str, Any]:
    """新增服务商（name 唯一 + base_url 校验 + models 非空）"""
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="服务商名称不能为空")
    models = _validate_models(models)
    _validate_unique_name(db, name)
    _validate_base_url(base_url)

    provider = AiProvider(
        name=name,
        base_url=base_url.strip(),
        api_key=api_key.strip(),
        models=models,
        enabled=1 if enabled else 0,
        sort_order=sort_order,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _build_provider_item(provider)


def update_provider(
    db: Session,
    provider_id: int,
    name: str,
    base_url: str,
    api_key: str,
    models: list[str],
    enabled: bool = True,
    sort_order: int = 0,
) -> dict[str, Any]:
    """编辑服务商（name 唯一性 + base_url 校验；api_key 留空 = 保持不变）"""
    provider = db.query(AiProvider).filter(AiProvider.id == provider_id).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="服务商不存在")
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="服务商名称不能为空")
    models = _validate_models(models)
    _validate_unique_name(db, name, exclude_id=provider_id)
    _validate_base_url(base_url)

    provider.name = name
    provider.base_url = base_url.strip()
    provider.models = models
    provider.enabled = 1 if enabled else 0
    provider.sort_order = sort_order
    if api_key.strip():
        provider.api_key = api_key.strip()
    db.commit()
    db.refresh(provider)
    return _build_provider_item(provider)


def delete_provider(db: Session, provider_id: int) -> dict[str, Any]:
    """删除服务商（被 ai.provider 选中引用时拒绝）"""
    from app.services.config_service import get_config_value

    provider = db.query(AiProvider).filter(AiProvider.id == provider_id).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="服务商不存在")
    selected = get_config_value(db, "ai.provider") or "custom"
    if selected == provider.name:
        raise HTTPException(
            status_code=409,
            detail=f"服务商「{provider.name}」正被 ai.provider 引用，请先在配置中切换服务商",
        )
    db.delete(provider)
    db.commit()
    return {"message": f"服务商「{provider.name}」已删除"}


def get_provider_by_name(db: Session, name: str) -> AiProvider | None:
    """按名称查启用服务商（供运行时引用解析）"""
    return db.query(AiProvider).filter(AiProvider.name == name, AiProvider.enabled == 1).first()


def list_provider_options(db: Session) -> list[str]:
    """服务商下拉选项：启用服务商 name + custom（供 ai.provider select）"""
    names = [
        row[0]
        for row in db.query(AiProvider.name)
        .filter(AiProvider.enabled == 1)
        .order_by(AiProvider.sort_order, AiProvider.id)
        .all()
    ]
    return [*names, "custom"]
