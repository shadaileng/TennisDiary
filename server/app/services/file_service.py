"""文件服务层：路径工具 + MD5 计算 + File 记录操作 + 引用计数管理

解耦各路由中的重复文件操作逻辑，统一维护。
"""

import hashlib
import os
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.file import File

log = get_logger("user")


# ==================== 路径工具 ====================


def resolve_safe_path(rel_path: str) -> str | None:
    """将相对路径解析为 UPLOAD_DIR 内的绝对路径，越界返回 None"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    candidate = os.path.normpath(os.path.join(upload_dir, rel_path))
    if candidate != upload_dir and candidate.startswith(upload_dir + os.sep):
        return candidate
    return None


def rel_path_to_abs(rel_path: str) -> str:
    """相对路径 → 绝对路径（不校验，用于已知合法路径）"""
    return os.path.abspath(os.path.join(settings.UPLOAD_DIR, rel_path))


def abs_path_to_rel(abs_path: str) -> str:
    """绝对路径 → 相对路径（正斜杠）"""
    return os.path.relpath(abs_path, settings.UPLOAD_DIR).replace(os.sep, "/")


def build_upload_dir(base_dir: str, user_id: int) -> str:
    """构建并返回 UPLOAD_DIR/base_dir/{user_id}/ 绝对路径（自动创建）"""
    rel_dir = os.path.join(base_dir, str(user_id))
    abs_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, rel_dir))
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


def make_rel_path(base_dir: str, user_id: int, filename: str) -> str:
    """生成 {base_dir}/{user_id}/{filename} 格式相对路径（正斜杠）"""
    return os.path.join(base_dir, str(user_id), filename).replace(os.sep, "/")


def file_exists(abs_path: str) -> bool:
    """安全判断文件是否存在（异常时返回 False）"""
    try:
        return os.path.isfile(abs_path)
    except (OSError, ValueError):
        return False


def get_file_size(abs_path: str) -> int:
    """获取文件大小（字节），文件不存在返回 0"""
    try:
        return os.path.getsize(abs_path)
    except (OSError, ValueError):
        return 0


def safe_unlink(abs_path: str) -> bool:
    """安全删除文件，不存在时不抛错，返回是否成功删除"""
    try:
        if os.path.isfile(abs_path):
            os.unlink(abs_path)
            return True
        return False
    except (OSError, ValueError) as exc:
        log.warning("文件删除失败: %s", exc)
        return False


# ==================== MD5 计算 ====================


def compute_md5(file_obj, chunk_size: int = 8192) -> str:
    """流式计算文件 MD5（避免大文件内存溢出）"""
    md5 = hashlib.md5()
    while chunk := file_obj.read(chunk_size):
        md5.update(chunk)
    file_obj.seek(0)  # 重置文件指针
    return md5.hexdigest()


def compute_md5_from_path(abs_path: str, chunk_size: int = 8192) -> str | None:
    """从文件路径计算 MD5，文件不存在返回 None"""
    if not os.path.isfile(abs_path):
        return None
    try:
        with open(abs_path, "rb") as f:
            return compute_md5(f, chunk_size)
    except (OSError, ValueError) as exc:
        log.warning("MD5 计算失败: path=%s error=%s", abs_path, exc)
        return None


# ==================== File 记录操作 ====================


def get_or_create_file(
    db: Session,
    user_id: int,
    md5: str,
    rel_path: str,
    upload_source: str,
    original_name: str = "",
    size_bytes: int = 0,
    mime_type: str = "",
) -> tuple[File, bool]:
    """获取或创建 File 记录（秒传主入口）

    返回：(File 记录, 是否秒传)
    """
    # 查询是否存在相同 MD5 的有效记录
    existing = (
        db.query(File)
        .filter(
            File.user_id == user_id,
            File.md5 == md5,
            File.deleted_at.is_(None),
        )
        .first()
    )

    if existing and existing.ref_count > 0:
        # 秒传：复用物理文件路径，创建新记录（自动处理 original_name 唯一）
        unique_name = ensure_unique_name(db, user_id, original_name)
        new_record = File(
            user_id=user_id,
            md5=md5,
            original_name=unique_name,
            rel_path=existing.rel_path,  # 复用路径
            size_bytes=existing.size_bytes,
            mime_type=existing.mime_type,
            upload_source=upload_source,
            ref_count=1,
            created_at=time.time(),
        )
        db.add(new_record)
        # 递增原记录的引用计数
        existing.ref_count += 1
        return new_record, True

    # 正常上传：创建新记录（自动处理 original_name 唯一）
    unique_name = ensure_unique_name(db, user_id, original_name)
    new_record = File(
        user_id=user_id,
        md5=md5,
        original_name=unique_name,
        rel_path=rel_path,
        size_bytes=size_bytes,
        mime_type=mime_type,
        upload_source=upload_source,
        ref_count=1,
        created_at=time.time(),
    )
    db.add(new_record)
    return new_record, False


def ensure_unique_name(db: Session, user_id: int, original_name: str) -> str:
    """检查 (user_id, original_name) 是否已存在，存在则追加后缀"""
    base, ext = os.path.splitext(original_name)
    candidate = original_name
    counter = 1
    while (
        db.query(File)
        .filter(
            File.user_id == user_id,
            File.original_name == candidate,
            File.deleted_at.is_(None),
        )
        .first()
    ):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate


def is_file_owned(db: Session, user, rel_path: str) -> bool:
    """检查文件是否属于当前用户（查 File 表）"""
    return (
        db.query(File)
        .filter(
            File.user_id == user.id,
            File.rel_path == rel_path,
            File.deleted_at.is_(None),
            File.ref_count > 0,
        )
        .first()
        is not None
    )


def decrement_ref_count(db: Session, user_id: int, rel_path: str) -> int:
    """递减指定文件的引用计数，返回实际递减的数量"""
    record = (
        db.query(File)
        .filter(
            File.user_id == user_id,
            File.rel_path == rel_path,
            File.deleted_at.is_(None),
        )
        .first()
    )

    if not record:
        return 0

    record.ref_count = max(0, record.ref_count - 1)
    if record.ref_count <= 0:
        record.deleted_at = time.time()
    return 1


def decrement_analysis_files(db: Session, analysis) -> int:
    """递减 Analysis 关联的所有文件（含骨架产物）的引用计数"""
    import json

    count = 0
    # 主文件（thumb、video_url）
    if analysis.thumb:
        count += decrement_ref_count(db, analysis.user_id, analysis.thumb)
    if analysis.video_url:
        count += decrement_ref_count(db, analysis.user_id, analysis.video_url)

    # highlights（JSON 数组）
    if analysis.highlights:
        try:
            highlights_raw = analysis.highlights
            if isinstance(highlights_raw, str):
                highlights = json.loads(highlights_raw)
            else:
                highlights = highlights_raw
            if isinstance(highlights, list):
                for path in highlights:
                    count += decrement_ref_count(db, analysis.user_id, path)
        except (json.JSONDecodeError, TypeError):
            pass

    # 骨架产物（从 pose JSON 提取）
    if analysis.pose:
        try:
            pose = json.loads(analysis.pose) if isinstance(analysis.pose, str) else analysis.pose
            if isinstance(pose, dict):
                for path in pose.get("skeleton_frames") or []:
                    count += decrement_ref_count(db, analysis.user_id, path)
                skeleton_video = pose.get("skeleton_video_url")
                if skeleton_video:
                    count += decrement_ref_count(db, analysis.user_id, skeleton_video)
                skeleton_thumb = pose.get("skeleton_thumb")
                if skeleton_thumb:
                    count += decrement_ref_count(db, analysis.user_id, skeleton_thumb)
        except (json.JSONDecodeError, TypeError):
            pass

    return count


def register_ai_files(
    db: Session,
    user_id: int,
    paths: list[str],
    business_type: str,
    business_id: int,
) -> list[File]:
    """批量注册 AI 生成的文件（骨架帧/骨架视频等）到 File 表"""
    registered = []
    for rel_path in paths:
        abs_path = rel_path_to_abs(rel_path)
        md5 = compute_md5_from_path(abs_path)
        if not md5:
            log.warning("骨架文件 MD5 计算失败，跳过: %s", rel_path)
            continue

        size = get_file_size(abs_path)
        record = File(
            user_id=user_id,
            md5=md5,
            original_name=os.path.basename(rel_path),
            rel_path=rel_path,
            size_bytes=size,
            upload_source="skeleton",
            business_type=business_type,
            business_id=business_id,
            ref_count=1,
            created_at=time.time(),
        )
        db.add(record)
        registered.append(record)

    return registered


def cleanup_orphan_files(db: Session, days: int = 30) -> int:
    """清理已删除超过 N 天的物理文件，返回清理的文件数量"""
    import time as _time

    cutoff = _time.time() - (days * 86400)
    orphan_records = (
        db.query(File)
        .filter(
            File.deleted_at.isnot(None),
            File.deleted_at < cutoff,
        )
        .all()
    )

    cleaned = 0
    for record in orphan_records:
        abs_path = rel_path_to_abs(record.rel_path)
        if safe_unlink(abs_path):
            cleaned += 1
            log.info("清理已删除文件: %s", record.rel_path)
        # 删除记录
        db.delete(record)

    return cleaned


# ==================== 文件扫描 ====================


def _infer_upload_source(rel_path: str) -> str:
    """从路径推断上传来源"""
    parts = rel_path.split("/")
    if len(parts) < 2:
        return "other"

    prefix = parts[0].lower()
    if prefix == "avatars":
        return "avatar"
    elif prefix == "gears":
        return "gear_image"
    elif prefix == "videos":
        return "video"
    elif prefix in ("analyses", "frames"):
        return "video_frame"
    elif prefix == "images":
        return "gear_image"
    return "other"


def _infer_user_id(rel_path: str) -> int | None:
    """从路径推断用户 ID（如 avatars/1/xxx.jpg → 1）"""
    parts = rel_path.split("/")
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return None


def scan_orphan_files(db: Session) -> dict:
    """扫描 uploads 目录，返回未在 File 表中注册的文件列表"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    registered_paths = {
        r[0] for r in db.query(File.rel_path).filter(File.deleted_at.is_(None)).all()
    }

    orphans = []
    total_files = 0
    total_orphan_size = 0

    for root, _dirs, files in os.walk(upload_dir):
        for filename in files:
            total_files += 1
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, upload_dir).replace(os.sep, "/")

            if rel_path not in registered_paths:
                try:
                    stat = os.stat(abs_path)
                    orphan_size = stat.st_size
                    total_orphan_size += orphan_size
                    orphans.append(
                        {
                            "rel_path": rel_path,
                            "size_bytes": orphan_size,
                            "modified_at": stat.st_mtime,
                            "inferred_user_id": _infer_user_id(rel_path),
                            "inferred_source": _infer_upload_source(rel_path),
                        }
                    )
                except (OSError, ValueError) as exc:
                    log.warning("扫描文件失败: %s error=%s", rel_path, exc)

    return {
        "total_files": total_files,
        "registered_files": total_files - len(orphans),
        "orphan_files": len(orphans),
        "orphans": orphans,
        "total_orphan_size": total_orphan_size,
    }


def register_orphan_files(
    db: Session,
    rel_paths: list[str],
    default_user_id: int = 0,
) -> list[File]:
    """将孤立文件批量注册到 File 表"""
    registered = []

    for rel_path in rel_paths:
        abs_path = rel_path_to_abs(rel_path)

        # 检查文件是否存在
        if not os.path.isfile(abs_path):
            log.warning("文件不存在，跳过: %s", rel_path)
            continue

        # 检查是否已注册
        existing = (
            db.query(File).filter(File.rel_path == rel_path, File.deleted_at.is_(None)).first()
        )
        if existing:
            log.info("文件已注册，跳过: %s", rel_path)
            continue

        # 计算 MD5
        md5 = compute_md5_from_path(abs_path)
        size = get_file_size(abs_path)

        # 推断 user_id 和 upload_source
        user_id = _infer_user_id(rel_path) or default_user_id
        upload_source = _infer_upload_source(rel_path)

        record = File(
            user_id=user_id,
            md5=md5 or "",
            original_name=os.path.basename(rel_path),
            rel_path=rel_path,
            size_bytes=size,
            upload_source=upload_source,
            ref_count=1,
            created_at=time.time(),
        )
        db.add(record)
        registered.append(record)
        log.info("注册孤立文件: %s user_id=%d source=%s", rel_path, user_id, upload_source)

    return registered
