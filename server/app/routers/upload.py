"""文件上传相关路由（头像 + 装备封面）

138：全部文件操作经 `file_service` 门面完成，路由不再自行造文件名/写盘/删盘。
文件名统一由门面按 `{md5}.{后缀}` 推导，落盘目录 `UPLOAD_DIR/{分类}/{user_id}/`。
"""

import os

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.decorators.audit import audit
from app.models.user import User
from app.schemas.common import ApiResponse, ErrorCode
from app.services import file_service
from app.services.content_security import ContentSecurityError, check_image_sync
from app.services.wx_service import code_to_openid

log = get_logger("user")

router = APIRouter(prefix="/api/upload", tags=["upload"])

# 允许的图片扩展名
_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_AVATAR_CATEGORY = "avatar"
_GEAR_CATEGORY = "gear_image"


def _save_image(
    db: Session,
    user_id: int,
    content: bytes,
    ext: str,
    original_name: str,
    category: str,
) -> tuple[object, str]:
    """写盘 + 落库（经门面），返回 (File 记录, 绝对路径)"""
    record, reused = file_service.register(
        db=db,
        user_id=user_id,
        content=content,
        category=category,
        original_name=original_name,
        ext=ext,
    )
    db.commit()
    abs_path = file_service.abs_of(record.rel_path)
    log.info(
        "图片登记完成",
        user_id=user_id,
        rel_path=record.rel_path,
        category=category,
        reused=reused,
    )
    return record, abs_path


def _run_security_check(db: Session, user_id: int, record, abs_path: str) -> bool:
    """内容安全检查并落标记，返回是否通过"""
    try:
        check_image_sync(abs_path, str(user_id))
    except ContentSecurityError:
        log.warning("图片内容安全检查不通过", user_id=user_id)
        return False
    except Exception as exc:
        log.error("图片安全检查异常: %s", exc, exc_info=True)

    file_service.mark_security_checked(db, user_id, record.rel_path, True)
    db.commit()
    return True


@router.post("/avatar", response_model=ApiResponse[dict])
@audit(action="UPLOAD", resource_type="upload")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传当前用户头像，返回可用于 <image> 展示的相对 URL

    - 仅接受 jpg/jpeg/png/webp 图片
    - 存储到 UPLOAD_DIR/avatars/<user_id>/<md5>.<ext>（同内容只存一份）
    - 返回 {"url": "avatars/<user_id>/<md5>.<ext>", "mirage": true/false}
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        log.warning("头像上传拒绝：非法扩展名", user_id=current_user.id, ext=ext)
        detail = "仅支持 jpg/jpeg/png/webp 图片"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    content = file.file.read()
    original_name = file.filename or ""

    record, abs_path = _save_image(
        db, current_user.id, content, ext, original_name, _AVATAR_CATEGORY
    )
    security_ok = _run_security_check(db, current_user.id, record, abs_path)

    if not security_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像内容可能包含违规信息，请检查后重试",
        ) from None

    log.info("头像上传成功", user_id=current_user.id, path=record.rel_path)
    return ApiResponse(data={"url": record.rel_path, "mirage": False})


@router.get("/avatar/{user_id}/{filename}")
def download_avatar(user_id: int, filename: str):
    """下载头像（公开访问，无需鉴权；URL 含 user_id + MD5 不可猜测）"""
    rel_path = f"avatars/{user_id}/{filename}"
    abs_path = file_service.resolve(rel_path)
    if abs_path is None or not file_service.exists(rel_path):
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
    - 存储到 UPLOAD_DIR/gears/<user_id>/<md5>.<ext>（同内容只存一份）
    - 返回 {"url": "gears/<user_id>/<md5>.<ext>", "mirage": true/false}
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        log.warning("装备图片上传拒绝：非法扩展名", user_id=current_user.id, ext=ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 jpg/jpeg/png/webp 图片"
        )

    content = file.file.read()
    original_name = file.filename or ""

    record, abs_path = _save_image(db, current_user.id, content, ext, original_name, _GEAR_CATEGORY)
    security_ok = _run_security_check(db, current_user.id, record, abs_path)

    if not security_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片内容可能包含违规信息，请检查后重试",
        ) from None

    log.info("装备图片上传成功", user_id=current_user.id, path=record.rel_path)
    return ApiResponse(data={"url": record.rel_path, "mirage": False})


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
    - 技术故障返回明确错误码，前端据此拒绝保存（133：不再 fail-open）

    Returns:
        {"safe": true}（通过）
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

    # 4) 临时文件 → imgSecCheck → finally 即删（临时文件不进受管目录）
    tmp_path = file_service.write_temp(content, ext)
    try:
        check_image_sync(tmp_path, openid)
        log.info("游客封面检查通过", openid=_mask_openid(openid))
    except ContentSecurityError:
        log.warning("游客封面检查不通过", openid=_mask_openid(openid))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片可能包含违规信息，请更换后重试",
        ) from None
    except Exception as exc:
        log.error("游客封面安全检查异常: %s", exc, exc_info=True)
        return ApiResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="安全检查服务异常，请重试",
            success=False,
            data=None,
        )
    finally:
        file_service.unlink_abs(tmp_path)
    return ApiResponse(data={"safe": True})


def _mask_openid(openid: str) -> str:
    """openid 脱敏（审计/日志不落明文隐私）"""
    if not openid:
        return ""
    return f"{openid[:4]}***{openid[-4:]}" if len(openid) > 8 else "***"


@router.post("/check", response_model=ApiResponse[dict])
def check_file(
    md5: str = Body(...),
    size_bytes: int = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """文件秒传预检（MD5 精确匹配）

    - 不上传文件，仅按 MD5 查询已有文件记录
    - 命中 + 安全通过 → {hit: true, safe: true, url}
    - 命中 + 安全未通过 → {hit: true, safe: false}
    - 未命中 → {hit: false}
    """
    existing = file_service.find_by_md5(db, current_user.id, md5)
    if existing is None:
        return ApiResponse(data={"hit": False})

    # 物理文件不存在视为未命中
    if not file_service.exists(existing.rel_path):
        return ApiResponse(data={"hit": False})

    return ApiResponse(
        data={
            "hit": True,
            "safe": bool(existing.security_checked),
            "url": existing.rel_path if existing.security_checked else None,
        }
    )
