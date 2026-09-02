"""Admin 文件管理路由"""

import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import ADMIN_JWT_ALGORITHM, ADMIN_JWT_SECRET, get_current_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.mime import EXTENSION_MIME
from app.decorators.audit import audit
from app.models.admin import Admin
from app.models.file import File
from app.schemas.admin_file import (
    AdminFileListResponse,
    AdminFileResponse,
    BatchDeleteRequest,
    CleanupOrphansRequest,
    RegisterFilesRequest,
    ScanResultResponse,
)
from app.schemas.common import ApiResponse
from app.services import file_service

log = get_logger("admin")

router = APIRouter(prefix="/api/admin/files", tags=["admin-files"])


def _file_to_response(
    file_record: File,
    db: Session,
    classifications: dict | None = None,
) -> AdminFileResponse:
    """将 File ORM 转换为 AdminFileResponse"""
    if classifications and file_record.id in classifications:
        usage_status, usage_reason = classifications[file_record.id]
    else:
        usage_status, usage_reason = file_service.classify_file_usage(db, file_record)

    return AdminFileResponse(
        id=file_record.id,
        user_id=file_record.user_id,
        md5=file_record.md5,
        original_name=file_record.original_name,
        rel_path=file_record.rel_path,
        size_bytes=file_record.size_bytes,
        mime_type=file_record.mime_type,
        upload_source=file_record.upload_source,
        ref_count=file_record.ref_count,
        business_type=file_record.business_type,
        business_id=file_record.business_id,
        created_at=file_record.created_at,
        usage_status=usage_status,
        usage_reason=usage_reason,
    )


@router.get("", response_model=ApiResponse[AdminFileListResponse])
def list_files(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None, description="按用户 ID 过滤"),
    upload_source: str | None = Query(None, description="按上传来源过滤"),
    business_type: str | None = Query(None, description="按业务类型过滤"),
    usage_status: str | None = Query(None, description="按使用状态过滤（实时计算）"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """文件管理列表（支持按用户/来源/业务类型/使用状态过滤）"""
    query = db.query(File).filter(File.deleted_at.is_(None))

    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    if upload_source:
        query = query.filter(File.upload_source == upload_source)
    if business_type:
        query = query.filter(File.business_type == business_type)

    # usage_status 是实时计算的，无法用 SQL WHERE，需在 Python 中筛选
    if usage_status:
        all_files = query.order_by(File.created_at.desc()).all()
        classifications = file_service.bulk_classify_files(db, all_files)
        matched = [f for f in all_files if classifications.get(f.id, ("", ""))[0] == usage_status]
        total = len(matched)
        paginated = matched[offset : offset + limit]
        return ApiResponse(
            data=AdminFileListResponse(
                items=[_file_to_response(f, db, classifications) for f in paginated],
                total=total,
                offset=offset,
                limit=limit,
            )
        )

    total = query.count()
    files = query.order_by(File.created_at.desc()).offset(offset).limit(limit).all()
    classifications = file_service.bulk_classify_files(db, files)

    return ApiResponse(
        data=AdminFileListResponse(
            items=[_file_to_response(f, db, classifications) for f in files],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/stats/summary", response_model=ApiResponse[dict])
def file_stats(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """文件统计摘要（总数、总大小、按来源分组 + 使用状态计数）"""
    from sqlalchemy import func

    total_count = db.query(File).filter(File.deleted_at.is_(None)).count()
    total_size = db.query(func.sum(File.size_bytes)).filter(File.deleted_at.is_(None)).scalar() or 0

    # marked_deleted：已软删等待物理清理
    marked_deleted = db.query(File).filter(File.deleted_at.isnot(None)).count()

    # unreferenced：通过批量 classify 判定
    all_files = db.query(File).filter(File.deleted_at.is_(None)).all()
    classifications = file_service.bulk_classify_files(db, all_files)
    unreferenced_count = sum(1 for st, _ in classifications.values() if st != "in_use")

    # 按来源分组统计
    source_stats = (
        db.query(File.upload_source, func.count(File.id), func.sum(File.size_bytes))
        .filter(File.deleted_at.is_(None))
        .group_by(File.upload_source)
        .all()
    )

    by_source = {
        source: {"count": count, "size_bytes": size or 0} for source, count, size in source_stats
    }

    return ApiResponse(
        data={
            "total_count": total_count,
            "total_size_bytes": total_size,
            "by_source": by_source,
            "marked_deleted_count": marked_deleted,
            "unreferenced_count": unreferenced_count,
        }
    )


@router.delete("/{file_id}", response_model=ApiResponse[None])
@audit(action="DELETE", resource_type="file", resource_id_key="file_id")
def delete_file(
    file_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除文件记录（软删；引用归零且无其他记录共享物理文件时一并删除磁盘文件）"""
    file_record = db.query(File).filter(File.id == file_id, File.deleted_at.is_(None)).first()
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    removed_disk = file_service.soft_delete_file(db, file_record)

    db.commit()
    log.info(
        "Admin 删除文件成功",
        file_id=file_id,
        admin_id=admin.id,
        ref_count=file_record.ref_count,
        removed_disk=removed_disk,
    )
    return ApiResponse(message="删除成功")


@router.post("/batch-delete", response_model=ApiResponse[dict])
@audit(action="DELETE", resource_type="file", resource_id_key="file_ids")
def batch_delete_files(
    body: BatchDeleteRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """批量删除文件（软删；复用单条删除的引用递减与物理清理逻辑）"""
    deleted = 0
    skipped = 0
    disk_removed = 0
    errors: list[str] = []

    if not body.file_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_ids 不能为空")

    for file_id in body.file_ids:
        file_record = db.query(File).filter(File.id == file_id, File.deleted_at.is_(None)).first()
        if file_record is None:
            skipped += 1
            errors.append(f"文件不存在或已删除: {file_id}")
            continue
        try:
            removed = file_service.soft_delete_file(db, file_record)
            deleted += 1
            if removed:
                disk_removed += 1
        except Exception as exc:
            log.error("批量删除文件失败: %s", exc, exc_info=True)
            errors.append(f"删除失败: {file_id}")
            continue

    db.commit()
    log.info(
        "Admin 批量删除文件",
        admin_id=admin.id,
        deleted=deleted,
        skipped=skipped,
        disk_removed=disk_removed,
    )
    return ApiResponse(
        data={
            "deleted": deleted,
            "skipped": skipped,
            "disk_removed": disk_removed,
            "errors": errors,
        },
        message=f"删除完成：成功 {deleted} 个，跳过 {skipped} 个",
    )


@router.post("/cleanup", response_model=ApiResponse[dict])
@audit(action="DELETE", resource_type="file_cleanup")
def cleanup_files(
    days: int = Query(30, ge=1, le=365, description="清理已删除超过 N 天的文件"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """物理文件清理：删除已软删超过 N 天的记录及其磁盘文件"""
    cleaned = file_service.cleanup_orphan_files(db, days=days)
    db.commit()
    log.info("Admin 清理孤儿文件", cleaned=cleaned, admin_id=admin.id)
    return ApiResponse(data={"cleaned": cleaned}, message=f"清理完成，共清理 {cleaned} 个文件")


@router.post("/cleanup-orphans", response_model=ApiResponse[dict])
@audit(action="DELETE", resource_type="file_cleanup_orphans")
def cleanup_orphan_files(
    body: CleanupOrphansRequest,
    admin: Admin = Depends(get_current_admin),
):
    """物理删除指定的孤儿文件（不在 File 表中注册的文件）"""
    cleaned = file_service.cleanup_orphan_paths(body.files)
    log.info("Admin 清理孤儿文件", cleaned=cleaned, admin_id=admin.id, paths=body.files[:5])
    return ApiResponse(data={"cleaned": cleaned}, message=f"清理完成，共清理 {cleaned} 个文件")


@router.post("/scan", response_model=ApiResponse[ScanResultResponse])
@audit(action="SCAN", resource_type="file_scan")
def scan_orphan_files(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """扫描 uploads 目录，返回未在 File 表中注册的孤立文件列表"""
    result = file_service.scan_orphan_files(db)
    log.info(
        "Admin 扫描孤立文件",
        admin_id=admin.id,
        total=result["total_files"],
        orphan=result["orphan_files"],
    )
    return ApiResponse(data=ScanResultResponse(**result))


@router.post("/register", response_model=ApiResponse[dict])
@audit(action="REGISTER", resource_type="file_register")
def register_files(
    body: RegisterFilesRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """将文件注册到 File 表；files 为空时扫描并注册全部孤儿"""
    if body.files:
        rel_paths = body.files
    else:
        scan_result = file_service.scan_orphan_files(db)
        rel_paths = [o["rel_path"] for o in scan_result["orphans"]]
        if not rel_paths:
            return ApiResponse(data={"registered": 0}, message="没有发现未注册的文件")

    registered = file_service.register_orphan_files(
        db,
        rel_paths=rel_paths,
        default_user_id=body.default_user_id,
    )
    db.commit()
    log.info(
        "Admin 注册孤立文件",
        admin_id=admin.id,
        count=len(registered),
        paths=rel_paths[:5],
    )
    return ApiResponse(
        data={"registered": len(registered)},
        message=f"成功注册 {len(registered)} 个文件",
    )


# ==================== 下载 ====================

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    """解析 Range 头，返回 (start, end) 闭区间"""
    m = _RANGE_RE.match(range_header)
    if not m:
        raise HTTPException(status_code=416, detail="Range 格式无效")
    start_s, end_s = m.group(1), m.group(2)
    if start_s:
        start = int(start_s)
        end = int(end_s) if end_s else file_size - 1
    elif end_s:
        start = file_size - int(end_s)
        end = file_size - 1
    else:
        raise HTTPException(status_code=416, detail="Range 格式无效")
    if start < 0 or end >= file_size or start > end:
        raise HTTPException(status_code=416, detail="Range 超出文件范围")
    return start, end


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    request: Request,
    token: str | None = Query(None, description="可选 token 查询参数（供 window.open 使用）"),
    db: Session = Depends(get_db),
):
    """分片下载文件（支持 Range 请求头，返回 206 Partial Content）"""
    # 手动鉴权：优先 header，回退 query 参数
    from app.models.admin import Admin as AdminModel

    header_token = request.headers.get("X-Auth-Token")
    jwt_token = header_token or token
    if not jwt_token:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = jwt.decode(jwt_token, ADMIN_JWT_SECRET, algorithms=[ADMIN_JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="无效的 token") from exc
    if payload.get("type") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    sub = payload.get("sub")
    if not sub or not sub.startswith("admin:"):
        raise HTTPException(status_code=401, detail="无效的 token")
    admin_id = int(sub.split(":")[1])
    admin = db.query(AdminModel).filter(AdminModel.id == admin_id).first()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
    file_record = db.query(File).filter(File.id == file_id).first()
    if file_record is None:
        raise HTTPException(status_code=404, detail="文件记录不存在")

    abs_path = file_service.resolve_safe_path(file_record.rel_path)
    if abs_path is None or not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    file_size = os.path.getsize(abs_path)
    filename = file_record.original_name or os.path.basename(abs_path)
    # 兜底：若文件名无扩展名，从 rel_path 推断
    if "." not in os.path.basename(filename):
        ext = os.path.splitext(file_record.rel_path)[1]
        if ext:
            filename = filename + ext
    media_type = (
        file_record.mime_type
        or EXTENSION_MIME.get(os.path.splitext(filename)[1].lower())
        or "application/octet-stream"
    )

    range_header = request.headers.get("range")
    if range_header:
        start, end = _parse_range(range_header, file_size)
        content_length = end - start + 1

        def _iter_range():
            with open(abs_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            _iter_range(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
            media_type=media_type,
        )

    return FileResponse(
        abs_path,
        media_type=media_type,
        filename=filename,
    )


class RepairRequest(BaseModel):
    """文件修复请求：扫描并修正 mime_type"""

    only_empty: bool = True
    upload_source: str | None = None


@router.post("/repair", response_model=ApiResponse[dict])
@audit(action="REPAIR", resource_type="file")
def repair_files(
    body: RepairRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """扫描 File 表，按物理文件真实类型重新探测并修正 mime_type（Step 116）

    默认仅修正 mime_type 为空的记录；传 only_empty=false 则全量校验。
    """
    result = file_service.repair_file_mime_types(
        db, only_empty=body.only_empty, upload_source=body.upload_source
    )
    log.info(
        "Admin 修复文件 MIME 类型",
        admin_id=admin.id,
        scanned=result["scanned"],
        repaired=result["repaired"],
    )
    return ApiResponse(data=result)
