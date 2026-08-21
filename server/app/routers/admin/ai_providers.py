"""Admin AI 服务商管理路由（/api/admin/config/providers）"""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.admin import Admin
from app.schemas.admin import AiProviderRequest, ProviderModelsCheckRequest
from app.schemas.common import ApiResponse
from app.services import ai_provider_service

log = get_logger("admin")

router = APIRouter(prefix="/api/admin/config/providers", tags=["admin-ai-providers"])

_CHECK_TIMEOUT_SECONDS = 15


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


def _extract_available_models(data: dict) -> list[str]:
    """从 OpenAI 兼容 /models 响应解析可用模型 ID（data[]/models[]，取 id/name/字符串）"""
    payload = data.get("data") if isinstance(data.get("data"), list) else None
    if payload is None:
        payload = data.get("models") if isinstance(data.get("models"), list) else None
    available: list[str] = []
    for item in payload or []:
        if isinstance(item, str):
            available.append(item)
        elif isinstance(item, dict):
            name = item.get("id") or item.get("name")
            if name:
                available.append(str(name))
    return available


async def _probe_model(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    """对单个模型发最小文本探测（max_tokens=1，不耗图片 token）

    模型名不存在时上游秒回非 200（如 503 model_not_found），探测即识别。
    """
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "ping"}],
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=_CHECK_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        return True, "可用"
    text = (resp.text or "")[:120].replace("\n", " ")
    return False, f"不可用（HTTP {resp.status_code}）：{text}"


@router.post("/check-models", response_model=ApiResponse[dict])
async def check_models(
    req: ProviderModelsCheckRequest,
    admin: Admin = Depends(require_permission("system:config")),
):
    """模型可用性校验：优先 list（GET {base_url}/models），不支持则逐模型 probe

    - list 模式：解析 /models 可用 ID，逐模型标记命中/未命中，并返回 available 列表；
    - probe 模式：逐模型发 max_tokens=1 文本探测（模型名不存在时上游秒回非 200）；
    - 连接/超时级失败返回 ok=False（镜像 ai-connect 语义）。
    """
    base_url = req.base_url.rstrip("/")
    url = f"{base_url}/models"
    headers = {}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"
    try:
        async with httpx.AsyncClient(timeout=_CHECK_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        return ApiResponse(data={"ok": False, "message": "连接超时（15 秒）", "url": url})
    except httpx.HTTPError as e:
        return ApiResponse(data={"ok": False, "message": f"网络异常: {e!s}", "url": url})

    if resp.status_code == 200:
        try:
            available = _extract_available_models(resp.json())
        except ValueError as exc:
            log.debug(f"AI 服务商模型列表 JSON 解析失败: {exc}")
            available = []
        if available:
            results = [
                {
                    "model": m,
                    "ok": m in available,
                    "message": "可用" if m in available else "不在服务商模型列表中",
                }
                for m in req.models
            ]
            return ApiResponse(
                data={
                    "ok": True,
                    "strategy": "list",
                    "available": available,
                    "results": results,
                }
            )
        # 200 但无法解析模型列表 → 回落 probe
    elif resp.status_code in (401, 403):
        return ApiResponse(
            data={
                "ok": False,
                "status_code": resp.status_code,
                "message": f"鉴权失败（HTTP {resp.status_code}），请检查 API Key",
            }
        )

    # probe 兜底：逐模型最小文本探测
    try:
        results = []
        for model in dict.fromkeys(req.models):
            ok, message = await _probe_model(base_url, req.api_key, model)
            results.append({"model": model, "ok": ok, "message": message})
    except httpx.TimeoutException:
        return ApiResponse(data={"ok": False, "message": "连接超时（15 秒）", "url": base_url})
    except httpx.HTTPError as e:
        return ApiResponse(data={"ok": False, "message": f"网络异常: {e!s}", "url": base_url})

    return ApiResponse(data={"ok": True, "strategy": "probe", "results": results})
