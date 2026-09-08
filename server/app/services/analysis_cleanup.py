"""孤儿 `processing` 分析记录清理（139 G4）

背景：管线异常中断后，若 `status="failed"` 因连接损坏等原因未写成功，
记录会永久停留在 `processing`，导致小程序端无限轮询 `GET /api/analyses`。

本模块提供**超时兜底**：把超过阈值仍处于 processing 的记录强制置 failed，
作为状态兜底（G2）与前端兜底（G4）之外的最后一道防线。

触发方式：
- 应用启动时执行一次
- `list_analyses` 惰性触发（带节流，默认 5 分钟一次）
"""

import json
import time

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.analysis import Analysis

log = get_logger("analysis_cleanup")

#: processing 超时阈值（秒），超过则强制置 failed
DEFAULT_TIMEOUT_S = 600.0

#: 惰性触发的节流间隔（秒）
THROTTLE_S = 300.0

#: 写入 pipeline_status.error 的说明文案
ERROR_TEXT = "分析超时，已自动置为失败"

# 上次惰性触发时间（模块级，仅用于节流）
_last_run_at = 0.0


def _parse_pipeline_status(raw: str | None) -> dict:
    """解析 pipeline_status JSON；非法或缺失时返回空 dict"""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def cleanup_stuck_processing(
    db: Session,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    now: float | None = None,
) -> int:
    """把超时仍为 processing 的记录置为 failed

    Args:
        db: 数据库会话
        timeout_s: 超时阈值（秒）
        now: 当前时间戳，测试可注入

    Returns:
        被清理的记录数
    """
    current = time.time() if now is None else now
    cutoff = current - timeout_s

    # created_at > 0 用于排除历史脏数据（该字段缺省为 0，时间戳无意义）
    rows = (
        db.query(Analysis.id, Analysis.pipeline_status)
        .filter(
            Analysis.status == "processing",
            Analysis.created_at > 0,
            Analysis.created_at < cutoff,
        )
        .all()
    )
    if not rows:
        return 0

    for analysis_id, raw in rows:
        pipeline_status = _parse_pipeline_status(raw)
        pipeline_status["error"] = ERROR_TEXT
        db.execute(
            sa_update(Analysis)
            .where(Analysis.id == analysis_id)
            .values(
                status="failed",
                pipeline_status=json.dumps(pipeline_status, ensure_ascii=False),
            )
        )
    db.commit()

    log.warning(
        "清理超时 processing 记录 count={} timeout_s={} error={}",
        len(rows),
        timeout_s,
        ERROR_TEXT,
    )
    return len(rows)


def maybe_cleanup_stuck_processing(
    db: Session,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    force: bool = False,
) -> int:
    """惰性触发清理（带节流，避免每次列表请求都扫描）

    Args:
        db: 数据库会话
        timeout_s: 超时阈值（秒）
        force: 跳过节流强制执行（启动与测试使用）

    Returns:
        被清理的记录数；被节流跳过时返回 0
    """
    global _last_run_at

    now = time.time()
    if not force and (now - _last_run_at) < THROTTLE_S:
        return 0

    _last_run_at = now
    return cleanup_stuck_processing(db, timeout_s=timeout_s, now=now)
