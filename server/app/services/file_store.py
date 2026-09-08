"""物理存储层（138 文件管理重构）

职责：路径推导、目录准备、MD5 计算、MIME 兜底、写盘与删盘。

**仅允许被 `app.services.file_service` 门面调用**，路由层与其它 service 禁止直接 import。
本模块不做任何数据库操作，也不含业务语义。
"""

import hashlib
import os
import shutil
import time

from app.core.config import settings
from app.core.logging import get_logger
from app.core.mime import detect_mime_type, mime_type_from_ext

log = get_logger("user")

# upload_source / category → 物理目录名（保留分类目录 + 用户隔离）
# 结构：UPLOAD_DIR/{目录}/{user_id}/{md5}.{后缀}
CATEGORY_DIRS: dict[str, str] = {
    "avatar": "avatars",
    "gear_image": "gears",
    "video": "videos",
    "video_playback": "videos",
    "video_frame": "videos",
    "skeleton": "videos",
    "skeleton_video": "videos",
    "skeleton_frame": "videos",
    "skeleton_thumb": "videos",
    "analysis_thumb": "videos",
}
DEFAULT_CATEGORY = "other"
DEFAULT_CATEGORY_DIR = "others"

# 路径前缀 → upload_source（孤儿文件登记时反推来源）
_DIR_TO_SOURCE: dict[str, str] = {
    "avatars": "avatar",
    "gears": "gear_image",
    "videos": "video",
    "analyses": "video_frame",
    "frames": "video_frame",
    "images": "gear_image",
}
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


# ==================== 分类与路径 ====================


def category_of(upload_source: str) -> str:
    """upload_source → 分类目录键（未知来源归入 other）"""
    return upload_source if upload_source in CATEGORY_DIRS else DEFAULT_CATEGORY


def dir_of(category: str) -> str:
    """分类键 → 物理目录名"""
    return CATEGORY_DIRS.get(category, DEFAULT_CATEGORY_DIR)


def normalize_ext(ext: str) -> str:
    """规范化扩展名：小写、保证前导点（空值返回空串）"""
    if not ext:
        return ""
    ext = ext.strip().lower()
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


def build_rel_path(user_id: int, md5: str, ext: str, category: str) -> str:
    """生成受管文件相对路径：`{目录}/{user_id}/{md5}.{后缀}`（正斜杠）"""
    return f"{dir_of(category)}/{user_id}/{md5}{normalize_ext(ext)}"


def build_abs_path(user_id: int, md5: str, ext: str, category: str) -> str:
    """生成受管文件绝对路径"""
    return abs_of(build_rel_path(user_id, md5, ext, category))


def ensure_dir(abs_path: str) -> None:
    """确保目标文件的父目录存在"""
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)


def abs_of(rel_path: str) -> str:
    """相对路径 → 绝对路径（不校验越界）"""
    return os.path.abspath(os.path.join(settings.UPLOAD_DIR, rel_path))


def rel_of(abs_path: str) -> str:
    """绝对路径 → 相对路径（正斜杠）"""
    return os.path.relpath(abs_path, settings.UPLOAD_DIR).replace(os.sep, "/")


def resolve(rel_path: str) -> str | None:
    """相对路径 → UPLOAD_DIR 内绝对路径，越界返回 None"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    candidate = os.path.normpath(os.path.join(upload_dir, rel_path))
    if candidate != upload_dir and candidate.startswith(upload_dir + os.sep):
        return candidate
    return None


# ==================== 元数据 ====================


def exists(rel_path: str) -> bool:
    """受管文件是否存在（相对路径，自动防越界）"""
    abs_path = resolve(rel_path)
    if abs_path is None:
        return False
    try:
        return os.path.isfile(abs_path)
    except (OSError, ValueError):
        return False


def size_of(rel_path: str) -> int:
    """受管文件大小（字节），不存在返回 0"""
    abs_path = resolve(rel_path)
    if abs_path is None:
        return 0
    try:
        return os.path.getsize(abs_path)
    except (OSError, ValueError):
        return 0


def md5_of(content: bytes | None = None, path: str | None = None) -> str | None:
    """计算 MD5（二选一入参），失败返回 None"""
    try:
        if content is not None:
            return hashlib.md5(content).hexdigest()
        if path is None:
            return None
        if not os.path.isfile(path):
            return None
        md5 = hashlib.md5()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                md5.update(chunk)
        return md5.hexdigest()
    except (OSError, ValueError) as exc:
        log.warning("MD5 计算失败: {}", exc)
        return None


def md5_and_size_of(path: str) -> tuple[str | None, int]:
    """一次读盘同时得到 MD5 与大小，文件不存在返回 (None, 0)"""
    if not os.path.isfile(path):
        return None, 0
    try:
        md5 = hashlib.md5()
        size = 0
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                md5.update(chunk)
                size += len(chunk)
        return md5.hexdigest(), size
    except (OSError, ValueError) as exc:
        log.warning("MD5 计算失败: {}", exc)
        return None, 0


def mime_of(
    abs_path: str | None,
    upload_source: str = "",
    mime_type: str = "",
    probe: bool = True,
) -> str:
    """补齐 mime_type：已传值不覆盖；probe=False 时仅做扩展名映射（零磁盘 I/O）"""
    if mime_type:
        return mime_type
    if not abs_path:
        return ""
    if not probe:
        return mime_type_from_ext(abs_path)
    try:
        return detect_mime_type(abs_path, upload_source)
    except Exception as exc:  # noqa: BLE001 - 探测失败不应阻断登记
        log.warning("MIME 探测失败，回退扩展名: {}", exc)
        return mime_type_from_ext(abs_path)


# ==================== 写盘 / 删盘 ====================


def write_bytes(abs_path: str, content: bytes) -> None:
    """写入字节内容（自动建目录），失败向上抛错由调用方处理"""
    ensure_dir(abs_path)
    with open(abs_path, "wb") as out:
        out.write(content)


def move_into_place(src_abs: str, dst_abs: str) -> None:
    """把临时产物移动到受管路径（自动建目录，跨设备时退化为复制 + 删除）"""
    if os.path.abspath(src_abs) == os.path.abspath(dst_abs):
        return
    ensure_dir(dst_abs)
    shutil.move(src_abs, dst_abs)


def copy_into_place(src_abs: str, dst_abs: str) -> None:
    """复制文件到受管路径（保留源文件，自动建目录）"""
    if os.path.abspath(src_abs) == os.path.abspath(dst_abs):
        return
    ensure_dir(dst_abs)
    shutil.copyfile(src_abs, dst_abs)


def write_temp(content: bytes, ext: str = "") -> str:
    """写临时文件（check_tmp 目录，不进受管文件表），返回绝对路径"""
    tmp_dir = os.path.join(settings.UPLOAD_DIR, "check_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    name = f"{time.time_ns():x}{normalize_ext(ext)}"
    abs_path = os.path.join(tmp_dir, name)
    with open(abs_path, "wb") as out:
        out.write(content)
    return abs_path


def unlink(rel_path: str) -> bool:
    """删除受管文件，不存在时不抛错，返回是否实际删除"""
    abs_path = resolve(rel_path)
    if abs_path is None:
        return False
    try:
        if os.path.isfile(abs_path):
            os.unlink(abs_path)
            return True
        return False
    except (OSError, ValueError) as exc:
        log.warning("文件删除失败: {}", exc)
        return False


def unlink_abs(abs_path: str) -> bool:
    """删除任意绝对路径文件（临时文件等），不存在时不抛错"""
    try:
        if os.path.isfile(abs_path):
            os.unlink(abs_path)
            return True
        return False
    except (OSError, ValueError) as exc:
        log.warning("文件删除失败: {}", exc)
        return False


# ==================== 孤儿文件推断 ====================


def infer_source(rel_path: str) -> str:
    """从相对路径反推 upload_source（用于孤儿文件登记）"""
    parts = rel_path.split("/")
    if len(parts) < 2:
        return "other"
    source = _DIR_TO_SOURCE.get(parts[0].lower())
    if source is None:
        return "other"
    if source == "video" and os.path.splitext(rel_path)[1].lower() in _IMAGE_EXTS:
        return "video_frame"
    return source


def infer_user_id(rel_path: str) -> int | None:
    """从相对路径推断用户 ID（如 avatars/1/xxx.jpg → 1）"""
    parts = rel_path.split("/")
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return None
