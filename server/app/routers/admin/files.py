"""Admin 文件管理路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.admin import Admin
from app.models.file import File
from app.schemas.admin_file import (
    AdminFileListResponse,
    AdminFileResponse,
    BatchDeleteRequest,
    CleanupOrphansRequest,
    DerivedFileInfo,
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
    """将 File ORM 转换为 AdminFileResponse，包含派生文件查询"""
    derived_files = []
    if file_record.business_type and file_record.business_id:
        derived_records = (
            db.query(File)
            .filter(
                File.business_type == file_record.business_type,
                File.business_id == file_record.business_id,
                File.id != file_record.id,
                File.deleted_at.is_(None),
            )
            .all()
        )
        derived_files = [
            DerivedFileInfo(
                id=d.id,
                rel_path=d.rel_path,
                upload_source=d.upload_source,
                business_type=d.business_type,
                business_id=d.business_id,
                size_bytes=d.size_bytes,
                mime_type=d.mime_type,
            )
            for d in derived_records
        ]

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
        derived_files=derived_files,
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
        matched = [
            f for f in all_files
            if classifications.get(f.id, ("", ""))[0] == usage_status
        ]
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

    return ApiResponse(
        data=AdminFileListResponse(
            items=[_file_to_response(f, db) for f in files],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{file_id}", response_model=ApiResponse[AdminFileResponse])
def get_file(
    file_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """文件详情（含派生文件列表）"""
    file_record = db.query(File).filter(File.id == file_id, File.deleted_at.is_(None)).first()
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return ApiResponse(data=_file_to_response(file_record, db))


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

    # unreferenced：通过 classify 逐条判定（stats 低频调用，可接受 N 次查询）
    unreferenced_count = 0
    for f in db.query(File).filter(File.deleted_at.is_(None)).all():
        status, _ = file_service.classify_file_usage(db, f)
        if status != "in_use":
            unreferenced_count += 1

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
    """将选中的文件注册到 File 表"""
    registered = file_service.register_orphan_files(
        db,
        rel_paths=body.files,
        default_user_id=body.default_user_id,
    )
    db.commit()
    log.info(
        "Admin 注册孤立文件",
        admin_id=admin.id,
        count=len(registered),
        paths=body.files[:5],  # 只记录前5个
    )
    return ApiResponse(
        data={"registered": len(registered)},
        message=f"成功注册 {len(registered)} 个文件",
    )


@router.post("/register-all", response_model=ApiResponse[dict])
@audit(action="REGISTER_ALL", resource_type="file_register")
def register_all_files(
    default_user_id: int = Query(0, description="默认用户 ID（路径无法推断时使用）"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """一键注册所有未注册文件"""
    # 先扫描
    scan_result = file_service.scan_orphan_files(db)
    orphan_paths = [o["rel_path"] for o in scan_result["orphans"]]

    if not orphan_paths:
        return ApiResponse(data={"registered": 0}, message="没有发现未注册的文件")

    # 批量注册
    registered = file_service.register_orphan_files(
        db,
        rel_paths=orphan_paths,
        default_user_id=default_user_id,
    )
    db.commit()
    log.info(
        "Admin 一键注册所有孤立文件",
        admin_id=admin.id,
        count=len(registered),
    )
    return ApiResponse(
        data={"registered": len(registered)},
        message=f"成功注册 {len(registered)} 个文件",
    )
