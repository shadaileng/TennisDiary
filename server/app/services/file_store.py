"""物理存储层（138 文件管理重构）

职责：路径推导、目录准备、MD5 计算、MIME 兜底、写盘与删盘。

**仅允许被 `app.services.file_service` 门面调用**，路由层与其它 service 禁止直接 import。
本模块不做任何数据库操作，也不含业务语义。
"""

import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone

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


# ==================== 分片上传会话（140：单文件定位写 + manifest 登记） ====================

CHUNK_ROOT = "tmp/chunks"  # UPLOAD_DIR/tmp/chunks/<user_id>/<md5>/
CHUNK_DATA_NAME = "data.bin"  # 最终文件的唯一载体（各片按 offset 定位写入）
CHUNK_MANIFEST_NAME = "manifest.json"  # 会话权威状态登记
CHUNK_MANIFEST_TMP = "manifest.json.tmp"  # 原子写临时名
CHUNK_MAX_BYTES = 8 * 1024 * 1024  # 单片上限（含容差，超出由门面拒）
_MD5_SESSION_RE = re.compile(r"^[0-9a-f]{32}$")


def utc_now_iso() -> str:
    """当前 UTC 时间（ISO8601，`Z` 后缀，与 87 时区规范一致）"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _chunk_dir_path(user_id: int, md5: str) -> str:
    """会话目录绝对路径（仅推导，不创建；md5 非法直接拒绝防路径穿越）"""
    if not _MD5_SESSION_RE.match(md5 or ""):
        raise ValueError(f"非法分片会话 key: {md5!r}")
    return os.path.abspath(os.path.join(settings.UPLOAD_DIR, CHUNK_ROOT, str(int(user_id)), md5))


def chunk_dir_abs(user_id: int, md5: str) -> str:
    """会话目录绝对路径（自动创建）"""
    path = _chunk_dir_path(user_id, md5)
    os.makedirs(path, exist_ok=True)
    return path


def chunk_data_abs(user_id: int, md5: str) -> str:
    """`data.bin` 绝对路径（自动建目录）"""
    return os.path.join(chunk_dir_abs(user_id, md5), CHUNK_DATA_NAME)


def pwrite_chunk(user_id: int, md5: str, offset: int, content: bytes) -> int:
    """定位写入 `data.bin` 的 `[offset, offset+len)` 区段，返回写入字节数

    用 `os.pwrite` 而非 `seek + write`：不依赖共享文件指针，多个写者各写各段天然安全
    （当前串行，为后续并发预留）。写完 `fsync` 保证「写成功」可被门面如实入账。
    中间未写的空洞由 OS 补零，无需预 `truncate`。
    """
    if offset < 0:
        raise ValueError(f"非法分片偏移量: {offset}")
    abs_path = chunk_data_abs(user_id, md5)
    fd = os.open(abs_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        written = os.pwrite(fd, content, offset)
        os.fsync(fd)
    finally:
        os.close(fd)
    return written


def data_size(user_id: int, md5: str) -> int:
    """`data.bin` 当前字节数（不存在返回 0）"""
    try:
        return os.path.getsize(os.path.join(_chunk_dir_path(user_id, md5), CHUNK_DATA_NAME))
    except (OSError, ValueError):
        return 0


def read_manifest(user_id: int, md5: str) -> dict | None:
    """读取会话 manifest；无会话 / JSON 损坏 / 非对象一律返回 None（由门面按无会话处理）"""
    path = os.path.join(_chunk_dir_path(user_id, md5), CHUNK_MANIFEST_NAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        log.warning("分片 manifest 读取失败: {}", exc)
        return None
    return data if isinstance(data, dict) else None


def write_manifest(user_id: int, md5: str, manifest: dict) -> None:
    """原子写入 manifest：临时文件 + `os.replace`（杜绝半截 JSON）

    失败向上抛错由门面处理；调用方应在「写盘成功后」才调用本函数入账。
    """
    session = chunk_dir_abs(user_id, md5)
    tmp_path = os.path.join(session, CHUNK_MANIFEST_TMP)
    final_path = os.path.join(session, CHUNK_MANIFEST_NAME)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, final_path)


def clear_chunks(user_id: int, md5: str) -> int:
    """删除整个分片会话目录，返回删除文件数（不存在返回 0）"""
    session = _chunk_dir_path(user_id, md5)
    if not os.path.isdir(session):
        return 0
    removed = sum(len(files) for _, _, files in os.walk(session))
    try:
        shutil.rmtree(session)
    except (OSError, ValueError) as exc:
        log.warning("分片会话目录删除失败: {}", exc)
        return 0
    return removed


def cleanup_expired_chunks(max_age_hours: int = 24) -> int:
    """清理超过 `max_age_hours` 无进展的分片会话，返回清理目录数

    判定时序：manifest `updated_at` → manifest 文件 mtime → 会话目录 mtime。
    """
    root = os.path.abspath(os.path.join(settings.UPLOAD_DIR, CHUNK_ROOT))
    if not os.path.isdir(root):
        return 0
    cutoff = time.time() - (max_age_hours * 3600)
    cleaned = 0
    for user_name in os.listdir(root):
        user_path = os.path.join(root, user_name)
        if not os.path.isdir(user_path) or not user_name.isdigit():
            continue
        for md5 in os.listdir(user_path):
            session = os.path.join(user_path, md5)
            if not os.path.isdir(session) or not _MD5_SESSION_RE.match(md5):
                continue
            if _session_last_active(session) >= cutoff:
                continue
            clear_chunks(int(user_name), md5)
            if not os.path.isdir(session):  # 空目录会话（removed=0）也应计入
                cleaned += 1
                log.info("清理过期分片会话: user_id={} md5={}", user_name, md5)
    return cleaned


def _session_last_active(session_abs: str) -> float:
    """会话最后活跃时间（时间戳，秒）"""
    manifest_path = os.path.join(session_abs, CHUNK_MANIFEST_NAME)
    if os.path.isfile(manifest_path):
        manifest = None
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, ValueError) as exc:
            log.warning("分片 manifest 读取失败，回退文件时间: {}", exc)
        if isinstance(manifest, dict):
            parsed = _parse_iso_utc(str(manifest.get("updated_at") or ""))
            if parsed is not None:
                return parsed
        try:
            return os.path.getmtime(manifest_path)
        except OSError:
            pass
    try:
        return os.path.getmtime(session_abs)
    except OSError:
        return time.time()


def _parse_iso_utc(value: str) -> float | None:
    """ISO8601 → 时间戳（无时区按 UTC 处理），解析失败返回 None"""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()
