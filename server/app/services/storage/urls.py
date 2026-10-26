"""响应层两态外链（147 §6：一处收口，前端零改动）

两态规则（§6.1）：
- `SYNCED` 且位置即当前后端 → 绝对签名外链（直连对象存储，不占后端带宽）
- 其余（`local` / `PENDING` / `FAILED` / dataURL / 绝对地址 / 无记录 / 未启用）→
  原样返回相对路径，走现有后端代理，永不 404

收口点：`ApiResponse.model_post_init` 调用 `rewrite_response_urls` —— 先遍历收集
候选 `rel_path`，**一次 `IN` 批量查询**建映射后再遍历改写（§6.2 N+1 防护）；
DB 永远只存 `rel_path`，外链动态生成（存量零迁移）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.core.database import current_session
from app.core.logging import get_logger
from app.models.file import STORAGE_STATUS_SYNCED, File
from app.services.storage.base import StorageError
from app.services.storage.config import load_storage_config
from app.services.storage.factory import resolve_backend

log = get_logger("user")

# 值本身就是受管相对路径的字段（§6.3 接入清单，与 file_refs.FILE_REF_SPECS 对应）
STRING_URL_FIELDS = frozenset({"avatar_url", "photo", "video_url", "thumb", "rel_path"})
# 值内部「装着」相对路径的容器字段（json_list / json_dict，逐层收集）
PATH_BAG_FIELDS = frozenset({"highlights", "pose"})

# 绝对地址 / 内联数据：本就可直通渲染，不参与查询
_ABSOLUTE_PREFIXES = ("http://", "https://", "data:", "blob:", "//")


def is_candidate(value: Any) -> bool:
    """是否可能是受管 `rel_path`（绝对地址 / dataURL / 非字符串一律判否）"""
    return isinstance(value, str) and bool(value) and not value.startswith(_ABSOLUTE_PREFIXES)


def build_public_url_map(db, rel_paths) -> dict[str, str]:
    """批量把 `rel_path` 映射为可访问地址（一次 `IN` 查询，列表接口 N+1 防护）

    Returns:
        `{rel_path: 绝对签名外链}`；未启用对象存储 / 未同步 / 无记录的路径**不入映射**
        （调用方按「查到才替换」回落相对路径）
    """
    if db is None or not rel_paths:
        return {}
    candidates = {path for path in rel_paths if is_candidate(path)}
    if not candidates:
        return {}

    cfg = load_storage_config(db)
    if cfg.is_local:
        return {}  # 回滚开关档位：全部走代理，零额外开销

    rows = (
        db.query(File.rel_path)
        .filter(
            File.rel_path.in_(sorted(candidates)),
            File.deleted_at.is_(None),
            File.storage == cfg.backend,
            File.storage_status == STORAGE_STATUS_SYNCED,
        )
        .all()
    )
    if not rows:
        return {}

    backend = resolve_backend(cfg)
    mapping: dict[str, str] = {}
    for (rel_path,) in rows:
        try:
            url = backend.presign_get(rel_path)
        except StorageError as exc:
            # 签发失败不阻断响应：该条回落代理，其余照常外链
            log.warning("签名外链生成失败，回落代理: {} {}", rel_path, exc)
            continue
        if url:
            mapping[rel_path] = url
    return mapping


def to_public_url(db, rel_path: str) -> str:
    """单条 `rel_path` → 可访问地址（SYNCED 走签名外链，否则原样返回）"""
    if not is_candidate(rel_path):
        return rel_path
    return build_public_url_map(db, [rel_path]).get(rel_path, rel_path)


# ==================== 响应树遍历（收集 → 批量映射 → 改写） ====================


def _map_str(value: Any, found: set[str] | None, mapping: dict[str, str] | None) -> Any:
    """收集模式记入候选；改写模式查映射（查不到保持原值）"""
    if not is_candidate(value):
        return value
    if found is not None:
        found.add(value)
        return value
    return (mapping or {}).get(value, value)


def _walk_paths(value: Any, found: set[str] | None, mapping: dict[str, str] | None) -> Any:
    """容器字段（`highlights` / `pose`）逐层收集或改写其中的路径字符串"""
    if is_candidate(value):
        return _map_str(value, found, mapping)
    if isinstance(value, list):
        for index, item in enumerate(value):
            new = _walk_paths(item, found, mapping)
            if new is not item:
                value[index] = new
        return value
    if isinstance(value, dict):
        for key in list(value):
            new = _walk_paths(value[key], found, mapping)
            if new is not value[key]:
                value[key] = new
        return value
    return value


def _walk(node: Any, found: set[str] | None, mapping: dict[str, str] | None) -> Any:
    """遍历响应树：`found` 收集候选 / `mapping` 原地改写（二者互斥）

    - Pydantic 模型：按字段名命中 `STRING_URL_FIELDS` / `PATH_BAG_FIELDS`，
      其余字段仅递归（不按值猜测，避免误改普通字符串）
    - dict：键名同字段名规则（覆盖 `data={...}` 与嵌套 JSON）
    - list：逐元素递归（分页 `items`、列表响应）
    """
    if isinstance(node, BaseModel):
        for name in node.__pydantic_fields__:
            value = getattr(node, name, None)
            if name in STRING_URL_FIELDS:
                new = _map_str(value, found, mapping)
            elif name in PATH_BAG_FIELDS:
                new = _walk_paths(value, found, mapping)
            else:
                new = _walk(value, found, mapping)
            if mapping is not None and new is not value:
                setattr(node, name, new)
        return node
    if isinstance(node, dict):
        for key in list(node):
            value = node[key]
            if key in STRING_URL_FIELDS:
                new = _map_str(value, found, mapping)
            elif key in PATH_BAG_FIELDS:
                new = _walk_paths(value, found, mapping)
            else:
                new = _walk(value, found, mapping)
            if mapping is not None and new is not value:
                node[key] = new
        return node
    if isinstance(node, list):
        for index, item in enumerate(node):
            new = _walk(item, found, mapping)
            if mapping is not None and new is not item:
                node[index] = new
        return node
    return node


def rewrite_response_urls(db, data: Any) -> None:
    """响应构造时的两态改写（`ApiResponse.model_post_init` 唯一入口）

    - 无绑定会话（后台任务 / 直接构造）→ 跳过，返回相对路径走代理
    - 改写后的值是绝对地址 → 再次遍历天然 no-op（序列化重复校验安全）
    - 任何异常只记日志，不影响响应返回
    """
    if data is None or db is None:
        return
    try:
        found: set[str] = set()
        _walk(data, found, None)
        if not found:
            return
        mapping = build_public_url_map(db, found)
        if mapping:
            _walk(data, None, mapping)
    except Exception as exc:
        log.exception("响应外链改写失败: {}", exc)


def rewrite_current_response(data: Any) -> None:
    """用当前请求绑定的会话改写（无会话时安全跳过）"""
    rewrite_response_urls(current_session(), data)
