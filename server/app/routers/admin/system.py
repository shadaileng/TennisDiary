"""系统监控路由"""

import shutil
import tarfile
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.backup_meta import BACKUP_META_DB_NAME, get_backup_meta_db
from app.core.config import settings
from app.core.database import get_db
from app.models.admin import Admin
from app.models.backup_record import BackupRecord
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/admin/system", tags=["admin-system"])

# 上传备份允许的扩展名
_BACKUP_ALLOWED_EXT = {".tar.gz", ".db"}


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
                if level:
                    # loguru 输出格式：`INFO     `（无方括号，大写）
                    if f"{level.upper():<8}" not in line:
                        continue
                if keyword and keyword not in line:
                    continue
                logs.append(line.strip())
                if len(logs) >= limit:
                    break
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"读取日志文件失败: {e!s}") from e

    return ApiResponse(data={"logs": logs, "total": len(logs)})


def _pack_data_dir(backup_path: Path) -> None:
    """将整个数据目录打包为 tar.gz，排除 backups 目录自身与临时文件"""
    data_dir = Path(settings.DATA_DIR).resolve()
    backup_dir = (data_dir / "backups").resolve()
    skip_suffixes = (".tmp", ".lock", ".pid")
    with tarfile.open(backup_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
        seen: set[str] = set()  # 已写入的 arcname，防止重复条目
        for item in sorted(data_dir.rglob("*")):
            # 跳过 backups 目录自身及其内部所有文件，避免递归膨胀
            if item == backup_dir or backup_dir in item.parents:
                continue
            # 跳过独立元数据库（不参与业务备份恢复，避免恢复时覆盖记录表）
            if item.is_file() and item.name == BACKUP_META_DB_NAME:
                continue
            # 跳过临时/锁文件
            if item.is_file() and item.suffix in skip_suffixes:
                continue
            try:
                arcname = str(item.relative_to(data_dir))
                # recursive=False：仅写当前条目，避免 tar.add 对目录递归
                # 展开内容导致同一文件被多个目录层级重复打包
                tar.add(item, arcname=arcname, recursive=False)
                seen.add(arcname)
            except OSError:
                continue


def _resolve_backup(backup_id: str) -> Path:
    """解析备份文件绝对路径并做路径穿越防护"""
    backup_dir = (Path(settings.DATA_DIR) / "backups").resolve()
    path = (backup_dir / backup_id).resolve()
    if path.parent != backup_dir:
        raise HTTPException(status_code=400, detail="非法备份标识")
    if not path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    return path


@router.post("/backup", response_model=ApiResponse[None])
def backup_database(
    admin: Admin = Depends(get_current_admin),
    meta_db: Session = Depends(get_backup_meta_db),
):
    """数据目录整体备份（tar.gz）"""
    data_dir = Path(settings.DATA_DIR).resolve()
    backup_dir = (data_dir / "backups").resolve()
    backup_dir.mkdir(exist_ok=True)

    # 数据库文件必须存在
    source_path = data_dir / "tennis_diary.db"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}_{uuid.uuid4().hex[:6]}.tar.gz"

    try:
        _pack_data_dir(backup_path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {e!s}") from e

    # 写入备份记录（独立元数据库）
    record = BackupRecord(
        name=backup_path.name,
        size=backup_path.stat().st_size,
        type="manual",
        status="created",
        created_by=admin.id,
    )
    meta_db.add(record)
    meta_db.commit()

    return ApiResponse(message=f"备份成功: {backup_path.name}")


@router.get("/backups", response_model=ApiResponse[dict])
def list_backups(
    admin: Admin = Depends(get_current_admin),
    meta_db: Session = Depends(get_backup_meta_db),
):
    """备份列表（纯表驱动，只查独立元数据库）"""
    records = (
        meta_db.query(BackupRecord)
        .filter(BackupRecord.deleted_at.is_(None))
        .order_by(BackupRecord.created_at.desc(), BackupRecord.id.desc())
        .all()
    )

    # 构建 id -> name 映射，用于还原「被恢复的备份」关联到的兜底备份文件名
    id_to_name = {r.id: r.name for r in records}

    backups = [
        {
            "name": r.name,
            "size": f"{r.size / (1024 * 1024):.2f} MB",
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "type": r.type,
            "status": r.status,
            "note": r.note,
            "restored_from_id": r.restored_from_id,
            "restored_from_name": (
                id_to_name.get(r.restored_from_id) if r.restored_from_id else None
            ),
        }
        for r in records
    ]

    return ApiResponse(data={"backups": backups, "total": len(backups)})


@router.get("/backup/download/{backup_id}", response_class=FileResponse)
def download_backup(
    backup_id: str,
    admin: Admin = Depends(get_current_admin),
):
    """下载备份文件"""
    backup_path = _resolve_backup(backup_id)
    return FileResponse(backup_path, media_type="application/gzip", filename=backup_path.name)


@router.post("/backup/upload", response_model=ApiResponse[dict])
def upload_backup(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
    meta_db: Session = Depends(get_backup_meta_db),
):
    """上传备份文件到 backups/ 目录（multipart 字段名 file）"""
    original_name = file.filename or ""
    ext = "".join(Path(original_name).suffixes).lower()  # 取全部后缀（如 .tar.gz）
    if ext not in _BACKUP_ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail="仅支持上传 .tar.gz 或 .db 备份文件",
        )

    backup_dir = (Path(settings.DATA_DIR) / "backups").resolve()
    backup_dir.mkdir(exist_ok=True)

    # 以 uuid 命名，避免与现有文件/记录冲突
    if ext == ".tar.gz":
        dest_path = backup_dir / f"upload_{uuid.uuid4().hex}.tar.gz"
    else:
        dest_path = backup_dir / f"upload_{uuid.uuid4().hex}.db"

    try:
        # 分块写入（复用上传模式，避免一次性读入内存）
        with open(dest_path, "wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e!s}") from e
    finally:
        file.file.close()

    record = BackupRecord(
        name=dest_path.name,
        size=dest_path.stat().st_size,
        type="upload",
        status="created",
        created_by=admin.id,
        note=f"上传自 {original_name}",
    )
    meta_db.add(record)
    meta_db.commit()

    return ApiResponse(
        data={"name": dest_path.name, "size": dest_path.stat().st_size},
        message="上传成功",
    )


@router.delete("/backup/{backup_id}", response_model=ApiResponse[None])
def delete_backup(
    backup_id: str,
    admin: Admin = Depends(get_current_admin),
    meta_db: Session = Depends(get_backup_meta_db),
):
    """删除备份记录（软删，保留审计痕迹；磁盘文件一并移除）"""
    backup_path = _resolve_backup(backup_id)

    record = (
        meta_db.query(BackupRecord)
        .filter(
            BackupRecord.name == backup_path.name,
            BackupRecord.deleted_at.is_(None),
        )
        .first()
    )

    # 物理删除磁盘文件
    try:
        backup_path.unlink()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e!s}") from e

    # 软删记录（保留审计）
    if record is not None:
        record.deleted_at = datetime.utcnow()
        record.status = "deleted"
        meta_db.commit()

    return ApiResponse(message="删除成功")


@router.post("/restore/{backup_id}", response_model=ApiResponse[None])
def restore_database(
    backup_id: str,
    admin: Admin = Depends(get_current_admin),
    meta_db: Session = Depends(get_backup_meta_db),
):
    """数据恢复（兼容 tar.gz 与旧 db）

    恢复前无条件生成一份完整兜底备份（pre_restore_*.tar.gz）并写入记录。
    独立元数据库 backup_meta.db 不参与备份恢复，因此记录表在恢复后仍完整保留。
    """
    backup_path = _resolve_backup(backup_id)
    data_dir = Path(settings.DATA_DIR).resolve()
    source_path = data_dir / "tennis_diary.db"

    try:
        # 恢复前无条件完整备份一份（兜底，可回退/删除）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_path = data_dir / "backups" / f"pre_restore_{timestamp}_{uuid.uuid4().hex[:6]}.tar.gz"
        _pack_data_dir(pre_path)

        if backup_path.name.endswith(".tar.gz"):
            # 整体恢复：解包回数据目录（含 uploads/logs/数据库）
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(data_dir)
        else:
            # 旧版 .db：仅恢复数据库文件
            shutil.copy2(backup_path, source_path)
    except (OSError, tarfile.TarError) as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {e!s}") from e

    # 写入 pre_restore 兜底记录 + 标记目标备份已用于恢复
    now = datetime.utcnow()
    pre_record = BackupRecord(
        name=pre_path.name,
        size=pre_path.stat().st_size,
        type="pre_restore",
        status="created",
        created_by=admin.id,
        note=f"恢复前兜底，目标 {backup_path.name}",
    )
    meta_db.add(pre_record)
    meta_db.flush()  # 拿到 pre_record.id 用于关联

    # 保证同时只有一个备份处于 restored 状态：先重置旧的 restored 记录
    (
        meta_db.query(BackupRecord)
        .filter(BackupRecord.status == "restored")
        .update(
            {
                BackupRecord.status: "created",
                BackupRecord.restored_at: None,
                BackupRecord.restored_by: None,
                BackupRecord.restored_from_id: None,
            },
            synchronize_session=False,
        )
    )

    # 标记目标备份已用于恢复，并关联到本次恢复前生成的兜底备份
    target = meta_db.query(BackupRecord).filter(BackupRecord.name == backup_path.name).first()
    if target is not None:
        target.status = "restored"
        target.restored_at = now
        target.restored_by = admin.id
        target.restored_from_id = pre_record.id
    meta_db.commit()

    return ApiResponse(message="恢复成功，请重启应用")
