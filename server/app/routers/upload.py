"""文件上传相关路由（头像 + 装备封面）"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.mime import detect_image_mime
from app.decorators.audit import audit
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import file_service
from app.services.content_security import ContentSecurityError, check_image_sync

log = get_logger("user")

router = APIRouter(prefix="/api/upload", tags=["upload"])

# 允许的图片扩展名
_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_AVATAR_DIR = "avatars"
_GEAR_DIR = "gears"


@router.post("/avatar", response_model=ApiResponse[dict])
@audit(action="UPLOAD", resource_type="upload")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传当前用户头像，返回可用于 <image> 展示的相对 URL

    - 仅接受 jpg/jpeg/png/webp 图片
    - 存储到 UPLOAD_DIR/avatars/<user_id>/<uuid>.<ext>
    - 返回 {"url": "avatars/<user_id>/<uuid>.<ext>", "mirage": true/false}
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        log.warning("头像上传拒绝：非法扩展名", user_id=current_user.id, ext=ext)
        detail = "仅支持 jpg/jpeg/png/webp 图片"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # 读取文件内容
    content = file.file.read()
    original_name = file.filename or ""

    # 构建目标路径
    abs_dir = file_service.build_upload_dir(_AVATAR_DIR, current_user.id)
    filename = f"{uuid.uuid4().hex}{ext}"
    rel_path = file_service.make_rel_path(_AVATAR_DIR, current_user.id, filename)
    abs_path = os.path.join(abs_dir, filename)

    # 写入物理文件
    try:
        with open(abs_path, "wb") as out:
            out.write(content)
    except Exception as exc:
        log.error("头像文件写入失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件写入失败，请稍后重试",
        ) from exc

    # 内容安全检查
    try:
        check_image_sync(abs_path, str(current_user.id))
    except ContentSecurityError:
        file_service.safe_unlink(abs_path)
        log.warning("头像内容安全检查不通过", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像内容可能包含违规信息，请检查后重试",
        ) from None
    except Exception as exc:
        file_service.safe_unlink(abs_path)
        log.error("头像安全检查异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="内容安全检查失败，请稍后重试",
        ) from exc

    # 创建 File 记录（秒传检测，MD5 由 get_or_create_file 从磁盘计算）
    file_record, is_mirage = file_service.get_or_create_file(
        db=db,
        user_id=current_user.id,
        rel_path=rel_path,
        abs_path=abs_path,
        upload_source="avatar",
        original_name=original_name,
        mime_type=file.content_type or "",
    )
    db.commit()

    # 秒传：删除刚写入的重复文件
    if is_mirage:
        file_service.safe_unlink(abs_path)
        abs_path = file_service.rel_path_to_abs(file_record.rel_path)

    # 用扩展名+PIL 探测真实图片类型，覆盖客户端缺失/错误的 Content-Type
    file_record.mime_type = detect_image_mime(abs_path)
    db.commit()

    log.info("头像上传成功", user_id=current_user.id, path=rel_path, mirage=is_mirage)
    return ApiResponse(data={"url": rel_path, "mirage": is_mirage})


@router.get("/avatar/{user_id}/{filename}")
def download_avatar(user_id: int, filename: str):
    """下载头像（公开访问，无需鉴权；URL 含 user_id + UUID 不可猜测）"""
    rel_path = file_service.make_rel_path(_AVATAR_DIR, user_id, filename)
    abs_path = file_service.resolve_safe_path(rel_path)
    if abs_path is None or not file_service.file_exists(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return FileResponse(abs_path)


@router.post("/gear-image", response_model=ApiResponse[dict])
@audit(action="UPLOAD", resource_type="upload")
def upload_gear_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传装备封面图片，返回可用于 <image> 展示的相对 URL

    - 仅接受 jpg/jpeg/png/webp 图片
    - 存储到 UPLOAD_DIR/gears/<user_id>/<uuid>.<ext>
    - 返回 {"url": "gears/<user_id>/<uuid>.<ext>", "mirage": true/false}
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        log.warning("装备图片上传拒绝：非法扩展名", user_id=current_user.id, ext=ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 jpg/jpeg/png/webp 图片"
        )

    # 读取文件内容
    content = file.file.read()
    original_name = file.filename or ""

    # 构建目标路径
    abs_dir = file_service.build_upload_dir(_GEAR_DIR, current_user.id)
    filename = f"{uuid.uuid4().hex}{ext}"
    rel_path = file_service.make_rel_path(_GEAR_DIR, current_user.id, filename)
    abs_path = os.path.join(abs_dir, filename)

    # 写入物理文件
    try:
        with open(abs_path, "wb") as out:
            out.write(content)
    except Exception as exc:
        log.error("装备图片文件写入失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件写入失败，请稍后重试",
        ) from exc

    # 文件已落盘：用扩展名+PIL 探测真实图片类型，覆盖客户端缺失/错误的 Content-Type
    file_record_mime = detect_image_mime(abs_path)

    # 内容安全检查
    try:
        check_image_sync(abs_path, str(current_user.id))
    except ContentSecurityError:
        file_service.safe_unlink(abs_path)
        log.warning("装备图片内容安全检查不通过", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片内容可能包含违规信息，请检查后重试",
        ) from None
    except Exception as exc:
        file_service.safe_unlink(abs_path)
        log.error("装备图片安全检查异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="内容安全检查失败，请稍后重试",
        ) from exc

    # 创建 File 记录（秒传检测，MD5 由 get_or_create_file 从磁盘计算）
    _file_record, is_mirage = file_service.get_or_create_file(
        db=db,
        user_id=current_user.id,
        rel_path=rel_path,
        abs_path=abs_path,
        upload_source="gear_image",
        original_name=original_name,
        mime_type=file_record_mime,
    )
    db.commit()

    # 秒传：删除刚写入的重复文件
    if is_mirage:
        file_service.safe_unlink(abs_path)

    log.info("装备图片上传成功", user_id=current_user.id, path=rel_path, mirage=is_mirage)
    return ApiResponse(data={"url": rel_path, "mirage": is_mirage})
