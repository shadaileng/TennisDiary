"""系统监控路由"""

import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.config import settings
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/admin/system", tags=["admin-system"])


def _format_uptime(seconds: float) -> str:
    """将秒数格式化为可读的运行时长字符串"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    parts.append(f"{secs}秒")

    return "".join(parts)


@router.get("/health", response_model=ApiResponse[dict])
def system_health(
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """系统健康检查增强"""
    try:
        # 数据库连通性
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except SQLAlchemyError as e:
        db_status = f"error: {e!s}"

    # 磁盘使用情况
    data_dir = Path(settings.DATA_DIR)
    try:
        total_size = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
        disk_usage = f"{total_size / (1024 * 1024):.2f} MB"
    except OSError:
        disk_usage = "unknown"

    # 运行时长
    start_time = getattr(request.app.state, "start_time", None)
    if start_time is not None:
        uptime_seconds = time.time() - start_time
        uptime = _format_uptime(uptime_seconds)
    else:
        uptime = "unknown"

    return ApiResponse(
        data={
            "status": "ok",
            "version": "1.0.0",
            "database": db_status,
            "disk_usage": disk_usage,
            "uptime": uptime,
        }
    )


@router.get("/stats", response_model=ApiResponse[dict])
def system_stats(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """运行时指标"""
    from app.models.analysis import Analysis
    from app.models.checkin import Checkin
    from app.models.diary import Diary
    from app.models.gear import Gear
    from app.models.post import Post
    from app.models.user import User
    from app.models.weight import WeightRecord

    # 各表数据量
    stats = {
        "users": db.query(User).count(),
        "diaries": db.query(Diary).count(),
        "gears": db.query(Gear).count(),
        "weights": db.query(WeightRecord).count(),
        "checkins": db.query(Checkin).count(),
        "analyses": db.query(Analysis).count(),
        "posts": db.query(Post).count(),
    }

    # 数据库大小
    db_path = Path(settings.DATA_DIR) / "tennis_diary.db"
    try:
        db_size = f"{db_path.stat().st_size / (1024 * 1024):.2f} MB"
    except OSError:
        db_size = "unknown"

    return ApiResponse(
        data={
            "stats": stats,
            "database_size": db_size,
        }
    )


@router.get("/logs", response_model=ApiResponse[dict])
def query_logs(
    level: str | None = None,
    keyword: str | None = None,
    limit: int = 100,
    admin: Admin = Depends(get_current_admin),
):
    """日志查询（支持按文件/级别/关键字过滤）"""
    log_file = Path(settings.LOG_DIR) / settings.LOG_FILE
    if not log_file.exists():
        return ApiResponse(data={"logs": [], "total": 0})

    logs = []
    try:
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                if level and f"[{level}]" not in line:
                    continue
                if keyword and keyword not in line:
                    continue
                logs.append(line.strip())
                if len(logs) >= limit:
                    break
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"读取日志文件失败: {e!s}") from e

    return ApiResponse(data={"logs": logs, "total": len(logs)})


@router.post("/backup", response_model=ApiResponse[None])
def backup_database(
    admin: Admin = Depends(get_current_admin),
):
    """数据库备份（SQLite在线备份）"""
    backup_dir = Path(settings.DATA_DIR) / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}.db"

    source_path = Path(settings.DATA_DIR) / "tennis_diary.db"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    try:
        # SQLite在线备份
        source = sqlite3.connect(str(source_path))
        dest = sqlite3.connect(str(backup_path))
        with dest:
            source.backup(dest)
        source.close()
        dest.close()
    except (OSError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {e!s}") from e

    return ApiResponse(message=f"备份成功: {backup_path.name}")


@router.get("/backups", response_model=ApiResponse[dict])
def list_backups(
    admin: Admin = Depends(get_current_admin),
):
    """备份列表"""
    backup_dir = Path(settings.DATA_DIR) / "backups"
    if not backup_dir.exists():
        return ApiResponse(data={"backups": [], "total": 0})

    backups = []
    for backup_file in backup_dir.glob("backup_*.db"):
        stat = backup_file.stat()
        backups.append(
            {
                "name": backup_file.name,
                "size": f"{stat.st_size / (1024 * 1024):.2f} MB",
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    # 按创建时间倒序
    backups.sort(key=lambda x: x["created_at"], reverse=True)

    return ApiResponse(data={"backups": backups, "total": len(backups)})


@router.post("/restore/{backup_id}", response_model=ApiResponse[None])
def restore_database(
    backup_id: str,
    admin: Admin = Depends(get_current_admin),
):
    """数据恢复"""
    backup_dir = Path(settings.DATA_DIR) / "backups"
    backup_path = backup_dir / f"{backup_id}.db"

    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")

    source_path = Path(settings.DATA_DIR) / "tennis_diary.db"

    try:
        # 备份当前数据库
        if source_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = backup_dir / f"pre_restore_{timestamp}.db"
            shutil.copy2(source_path, current_backup)

        # 恢复数据库
        shutil.copy2(backup_path, source_path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {e!s}") from e

    return ApiResponse(message="恢复成功，请重启应用")
