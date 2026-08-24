"""Admin 文件管理路由"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.admin import Admin
from app.models.file import File
from app.schemas.admin_file import AdminFileListResponse, AdminFileResponse, DerivedFileInfo
from app.schemas.common import ApiResponse
from app.services import file_service

log = get_logger("admin")

router = APIRouter(prefix="/api/admin/files", tags=["admin-files"])


def _file_to_response(file_record: File, db: Session) -> AdminFileResponse:
    """将 File ORM 转换为 AdminFileResponse，包含派生文件查询"""
    # 查询派生文件（相同 business_type + business_id 的其他文件）
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
    )


@router.get("", response_model=ApiResponse[AdminFileListResponse])
def list_files(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None, description="按用户 ID 过滤"),
    upload_source: str | None = Query(None, description="按上传来源过滤"),
    business_type: str | None = Query(None, description="按业务类型过滤"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """文件管理列表（支持按用户/来源/业务类型过滤）"""
    query = db.query(File).filter(File.deleted_at.is_(None))

    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    if upload_source:
        query = query.filter(File.upload_source == upload_source)
    if business_type:
        query = query.filter(File.business_type == business_type)

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
    """文件统计摘要（总数、总大小、按来源分组）"""
    from sqlalchemy import func

    total_count = db.query(File).filter(File.deleted_at.is_(None)).count()
    total_size = db.query(func.sum(File.size_bytes)).filter(File.deleted_at.is_(None)).scalar() or 0

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

    # 递减引用计数
    file_record.ref_count = max(0, file_record.ref_count - 1)
    removed_disk = False
    if file_record.ref_count <= 0:
        file_record.deleted_at = time.time()
        # 仅当无其他有效记录共享同一物理文件时才删除磁盘文件（秒传复用场景）
        shared = (
            db.query(File)
            .filter(
                File.rel_path == file_record.rel_path,
                File.id != file_record.id,
                File.deleted_at.is_(None),
            )
            .first()
        )
        if shared is None:
            abs_path = file_service.rel_path_to_abs(file_record.rel_path)
            removed_disk = file_service.safe_unlink(abs_path)

    db.commit()
    log.info(
        "Admin 删除文件成功",
        file_id=file_id,
        admin_id=admin.id,
        ref_count=file_record.ref_count,
        removed_disk=removed_disk,
    )
    return ApiResponse(message="删除成功")


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
