"""文件上传相关路由（头像 + 装备封面）"""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.mime import detect_image_mime
from app.decorators.audit import audit
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import file_service
from app.services.content_security import ContentSecurityError, check_image_sync
from app.services.wx_service import code_to_openid

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


@router.post("/guest-gear-check", response_model=ApiResponse[dict])
async def guest_gear_check(
    file: UploadFile = File(...),
    code: str = Form(...),
):
    """游客装备封面「仅检即弃」内容安全检查（免鉴权）

    - 不依赖 get_current_user、不建用户记录：游客无 token，需在保存封面当下联网做 imgSecCheck
    - code 为 wx.login 一次性 code → code_to_openid 换 openid（imgSecCheck 强要求 openid）
    - 写临时文件 → check_image_sync(imgSecCheck) → try/finally 即删
    - 不落盘、不建 File 记录、不写 DB（与 /gear-image 的「正式受检落盘」分离）
    - fail-open：微信/网络侧异常时返回 safe:true 放行（前端存本地 dataURL，
      同步正式上传 /gear-image 仍二次受检，最终入库封面必然通过官方检查）

    Returns:
        {"safe": true}（通过 / fail-open）
        违规 → 400
    """
    # 1) 类型校验
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        log.warning("游客封面检查拒绝：非法扩展名", ext=ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg/jpeg/png/webp 图片",
        )

    # 2) 大小校验（imgSecCheck 限 ≤1MB）
    content = file.file.read()
    if len(content) > 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片过大，请压缩后重试",
        )

    # 3) wx.login code → openid
    try:
        openid = await code_to_openid(code)
    except (ValueError, RuntimeError) as exc:
        log.warning("游客封面检查：code 换 openid 失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="登录态已过期，请重新进入小程序",
        ) from exc

    # 4) 写临时文件 → imgSecCheck → finally 即删
    tmp_dir = os.path.join(settings.UPLOAD_DIR, "check_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    abs_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}{ext}")
    try:
        with open(abs_path, "wb") as out:
            out.write(content)
        check_image_sync(abs_path, openid)
        log.info("游客封面检查通过", openid=_mask_openid(openid))
    except ContentSecurityError:
        log.warning("游客封面检查不通过", openid=_mask_openid(openid))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片可能包含违规信息，请更换后重试",
        ) from None
    except Exception as exc:
        # fail-open：微信/网络异常放行（正式上传兜底受检）；不把调用方错误当违规
        log.error("游客封面安全检查异常，放行: %s", exc, exc_info=True)
        return ApiResponse(data={"safe": True})
    finally:
        file_service.safe_unlink(abs_path)
    return ApiResponse(data={"safe": True})


def _mask_openid(openid: str) -> str:
    """openid 脱敏（审计/日志不落明文隐私）"""
    if not openid:
        return ""
    return f"{openid[:4]}***{openid[-4:]}" if len(openid) > 8 else "***"
