"""动态配置服务：DB 覆盖 > 环境变量默认值，请求时实时解析

- 配置定义见 app/core/config_registry.py；
- system_configs 表只存覆盖值，无覆盖行时即环境变量默认值（source=env）。
"""

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config_registry import (
    CONFIG_ITEMS,
    SOURCE_BUILTIN,
    SOURCE_DB,
    SOURCE_ENV,
    VALUE_TYPE_BOOL,
    VALUE_TYPE_INT,
    VALUE_TYPE_SECRET,
    VALUE_TYPE_SELECT,
    VALUE_TYPE_URL,
    find_config_item,
    list_categories,
)
from app.models.system_config import SystemConfig

MASK_PLACEHOLDER = "****"


def mask_secret(value: str) -> str:
    """通用敏感值掩码：{前3位}****{末4位}；过短或空值返回掩码/空串"""
    if not value:
        return ""
    if len(value) <= 8:
        return MASK_PLACEHOLDER
    return f"{value[:3]}{MASK_PLACEHOLDER}{value[-4:]}"


@dataclass(frozen=True)
class AIConfig:
    """AI 网关生效配置（服务商引用 > DB 覆盖 > env 默认）"""

    api_key: str
    base_url: str
    model: str
    provider: str = "custom"  # 当前生效服务商名；custom = 独立配置


def get_config_value(db: Session, key: str) -> str:
    """读取生效值：DB 覆盖 > 环境变量默认"""
    item = find_config_item(key)
    if item is None:
        return ""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row is not None and row.value is not None else item.default


def _get_override_value(db: Session, key: str) -> str | None:
    """仅返回显式覆盖值（无覆盖行 = None），区别于回退 env 默认的 get_config_value"""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row is not None and row.value is not None else None


def _resolve_ai_config(
    db: Session,
    api_key: str,
    base_url: str,
    model: str,
    provider_name: str,
) -> AIConfig:
    """按 ai.provider 引用解析：选中服务商则引用其条目，否则回落独立配置"""
    from app.services.ai_provider_service import get_provider_by_name

    if provider_name and provider_name != "custom":
        provider = get_provider_by_name(db, provider_name)
        if provider is not None:
            return AIConfig(
                api_key=provider.api_key or api_key,
                base_url=provider.base_url,
                model=_get_override_value(db, "ai.model") or provider.default_model,
                provider=provider.name,
            )
    return AIConfig(api_key=api_key, base_url=base_url, model=model, provider="custom")


def get_ai_config(db: Session) -> AIConfig:
    """AI 三件套生效配置（服务商引用 > 独立覆盖 > env 默认）"""
    provider_name = get_config_value(db, "ai.provider")
    return _resolve_ai_config(
        db,
        api_key=get_config_value(db, "ai.api_key"),
        base_url=get_config_value(db, "ai.base_url"),
        model=get_config_value(db, "ai.model"),
        provider_name=provider_name,
    )


def _build_item(db: Session, key: str) -> dict[str, Any]:
    """构造单个配置项响应（合并覆盖值 + 掩码 + 来源状态）"""
    item = find_config_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"配置项不存在: {key}")
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    default = item.default
    is_secret = item.value_type == VALUE_TYPE_SECRET

    if row is not None:
        effective = row.value or ""
        source = SOURCE_DB
    elif item.env_key is None:
        effective = default
        source = SOURCE_BUILTIN
    else:
        effective = default
        source = SOURCE_ENV

    return {
        "key": item.key,
        "category": item.category,
        "label": item.label,
        "description": item.description,
        "value_type": item.value_type,
        "editable": item.editable,
        "value": mask_secret(effective) if is_secret else effective,
        "has_value": bool(effective),
        "default_value": mask_secret(default) if is_secret else default,
        "source": source,
        "options": _item_options(db, item),
        "updated_at": row.updated_at.isoformat() if row is not None and row.updated_at else None,
        "updated_by": row.updated_by if row is not None else None,
    }


def _item_options(db: Session, item) -> list[str] | None:
    """select 项选项：静态取注册表；ai.provider 动态取服务商列表 + custom"""
    if item.key == "ai.provider":
        from app.services.ai_provider_service import list_provider_options

        return list_provider_options(db)
    return item.options


def _validate_value(item, value: str) -> str:
    """按 value_type 校验并归一化；非法值抛 400"""
    vtype = item.value_type
    if vtype == VALUE_TYPE_URL:
        if not value.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400, detail=f"{item.label} 必须是 http(s):// 开头的合法地址"
            )
        return value
    if vtype == VALUE_TYPE_BOOL:
        lowered = value.strip().lower()
        if lowered in ("true", "1"):
            return "true"
        if lowered in ("false", "0"):
            return "false"
        raise HTTPException(status_code=400, detail=f"{item.label} 必须是 true/false")
    if vtype == VALUE_TYPE_INT:
        try:
            int(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"{item.label} 必须是整数") from None
        return value.strip()
    if vtype == VALUE_TYPE_SELECT:
        if item.options and value not in item.options:
            raise HTTPException(
                status_code=400, detail=f"{item.label} 取值须为: {', '.join(item.options)}"
            )
        return value
    return value


def set_config_value(
    db: Session, key: str, value: str, admin_id: int | None = None
) -> dict[str, Any]:
    """设置覆盖值；secret 空值/掩码值=保持不变；等于默认值=归一化删行"""
    item = find_config_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"配置项不存在: {key}")
    if not item.editable:
        raise HTTPException(status_code=403, detail=f"配置项 {item.label} 不可动态编辑")

    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()

    if item.value_type == VALUE_TYPE_SECRET:
        current = row.value if row is not None else item.default
        if value == "" or value == mask_secret(current):
            db.commit()
            return _build_item(db, key)

    normalized = _validate_value(item, value)

    if normalized == item.default:
        if row is not None:
            db.delete(row)
            db.commit()
    else:
        if row is None:
            row = SystemConfig(key=key, value=normalized, updated_by=admin_id)
            db.add(row)
        else:
            row.value = normalized
            row.updated_by = admin_id
        db.commit()

    return _build_item(db, key)


def delete_config_value(db: Session, key: str) -> dict[str, Any]:
    """删除覆盖行（恢复默认）"""
    item = find_config_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"配置项不存在: {key}")
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row is not None:
        db.delete(row)
        db.commit()
    return _build_item(db, key)


def reset_all(db: Session) -> None:
    """清空全部覆盖行"""
    db.query(SystemConfig).delete()
    db.commit()


def list_config_items(db: Session) -> dict[str, Any]:
    """全量配置：summary + 分类 + items"""
    overrides = {row.key for row in db.query(SystemConfig).all()}
    items = [_build_item(db, item.key) for item in CONFIG_ITEMS]
    editable_total = sum(1 for i in items if i["editable"])
    categories = []
    for cat in list_categories():
        cat_items = [i for i in items if i["category"] == cat["key"]]
        categories.append(
            {
                "key": cat["key"],
                "label": cat["label"],
                "description": cat["description"],
                "item_count": cat["item_count"],
                "overridden": sum(1 for i in cat_items if i["key"] in overrides),
            }
        )
    return {
        "summary": {
            "total": len(items),
            "editable": editable_total,
            "overridden": len(overrides),
            "categories": categories,
        },
        "items": items,
    }
