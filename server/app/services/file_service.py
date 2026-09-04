"""文件服务层：路径工具 + MD5 计算 + File 记录操作 + 引用计数管理

解耦各路由中的重复文件操作逻辑，统一维护。
"""

import hashlib
import os
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.mime import detect_mime_type, mime_type_from_ext
from app.models.analysis import Analysis
from app.models.file import File
from app.models.gear import Gear
from app.models.user import User

log = get_logger("user")

# 文件使用边界（118 §5.8）：小程序实际消费判定
# 原片 / 抽帧帧图不被小程序直接消费，可直接清除（unreferenced）
NON_CONSUMED_SOURCES = {"video", "video_frame"}
# 需按 Analysis 路径匹配判定的上传源：播放短片 / 骨架产物 / 封面
# 131：补全实际登记值 skeleton_video/thumb/frame（此前只有存量 skeleton，导致误判未绑定业务）
ANALYSIS_MATCH_SOURCES = {
    "video_playback",
    "skeleton",
    "skeleton_video",
    "skeleton_thumb",
    "skeleton_frame",
    "analysis_thumb",
}
# 被小程序直接消费的源（含头像 / 装备图，二者另有独立匹配分支）
CONSUMED_SOURCES = ANALYSIS_MATCH_SOURCES | {"avatar", "gear_image"}


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


def compute_md5_from_bytes(data: bytes) -> str:
    """从字节数据计算 MD5"""
    return hashlib.md5(data).hexdigest()


def compute_md5_and_size(abs_path: str, chunk_size: int = 8192) -> tuple[str | None, int]:
    """一次磁盘读取同时计算 MD5 和文件大小

    Args:
        abs_path: 文件绝对路径
        chunk_size: 读取块大小

    Returns:
        (md5_hex, size_bytes) 元组，文件不存在返回 (None, 0)
    """
    if not os.path.isfile(abs_path):
        return None, 0
    try:
        md5 = hashlib.md5()
        size = 0
        with open(abs_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)
                size += len(chunk)
        return md5.hexdigest(), size
    except (OSError, ValueError) as exc:
        log.warning("MD5 计算失败: path=%s error=%s", abs_path, exc)
        return None, 0


# ==================== File 记录操作 ====================


def resolve_mime_type(
    abs_path: str | None,
    upload_source: str = "",
    mime_type: str = "",
    probe: bool = True,
) -> str:
    """补齐文件登记的 mime_type（131：登记入口统一兜底）

    Step 116 只覆盖了上传端点，骨架视频/封面、裁剪短片、报告落库、孤儿注册等
    入口都没有传 mime_type，落库为空字符串。此处由登记函数统一兜底：

    - mime_type 非空：尊重调用方传入值（上传端点已做服务端探测），不覆盖
    - probe=True：detect_mime_type 真实探测（PIL/ffprobe，读盘）
    - probe=False：仅确定性扩展名映射（零磁盘 I/O，供批量登记热路径使用）
    """
    if mime_type:
        return mime_type
    if not abs_path:
        return ""
    if not probe:
        return mime_type_from_ext(abs_path)
    try:
        return detect_mime_type(abs_path, upload_source)
    except Exception as exc:  # noqa: BLE001 - 探测失败不应阻断登记
        log.warning("MIME 探测失败，回退扩展名: path=%s error=%s", abs_path, exc)
        return mime_type_from_ext(abs_path)


def get_or_create_file(
    db: Session,
    user_id: int,
    rel_path: str,
    upload_source: str,
    original_name: str = "",
    abs_path: str | None = None,
    md5: str | None = None,
    size_bytes: int | None = None,
    mime_type: str = "",
    business_type: str | None = None,
    business_id: int | None = None,
) -> tuple[File, bool]:
    """获取或创建 File 记录（秒传主入口）

    abs_path：优先用，内部计算 md5/size_bytes
    md5/size_bytes：abs_path 不可用时由调用方显式传入（如内存中的上传内容已写盘后）
    返回：(File 记录, 是否秒传)
    """
    # 优先从磁盘计算 MD5
    if abs_path and not md5:
        md5 = compute_md5_from_path(abs_path)
    if not md5:
        raise ValueError(f"无法计算 MD5: abs_path={abs_path}")
    if size_bytes is None and abs_path:
        size_bytes = os.path.getsize(abs_path) if os.path.isfile(abs_path) else 0
    if size_bytes is None:
        size_bytes = 0
    # 131：登记兜底——调用方未传 mime 时按物理文件探测（已传值的不覆盖）
    abs_file = abs_path or (rel_path_to_abs(rel_path) if rel_path else None)
    mime_type = resolve_mime_type(abs_file, upload_source, mime_type)
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
        # 检查物理文件是否实际存在（防止 DB 记录残留但文件已被清理）
        existing_abs = rel_path_to_abs(existing.rel_path)
        if not os.path.isfile(existing_abs):
            log.warning(f"秒传目标文件不存在，转为普通上传: rel_path={existing.rel_path} md5={md5}")
            existing = None

    if existing and existing.ref_count > 0:
        # 秒传：复用物理文件路径，创建新记录（自动处理 original_name 唯一）
        unique_name = ensure_unique_name(db, user_id, original_name)
        new_record = File(
            user_id=user_id,
            md5=md5,
            original_name=unique_name,
            rel_path=existing.rel_path,  # 复用路径
            size_bytes=existing.size_bytes,
            # 131：存量记录 mime 为空时用本次探测值补齐，避免空值被秒传复制
            mime_type=existing.mime_type or mime_type,
            upload_source=upload_source,
            business_type=business_type,
            business_id=business_id,
            ref_count=1,
            created_at=time.time(),
        )
        db.add(new_record)
        # 递增原记录的引用计数
        existing.ref_count += 1
        db.flush()  # 确保后续 ensure_unique_name 能看到本条记录
        log.info(
            f"秒传命中: md5={md5[:12]}... size={existing.size_bytes} "
            f"reuse_path={existing.rel_path} source={upload_source} "
            f"existing_id={existing.id} new_id={new_record.id}"
        )
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
        business_type=business_type,
        business_id=business_id,
        ref_count=1,
        created_at=time.time(),
    )
    db.add(new_record)
    db.flush()  # 确保后续 ensure_unique_name 能看到本条记录
    log.info(
        f"新文件记录: md5={md5[:12]}... size={size_bytes} "
        f"path={rel_path} source={upload_source} file_id={new_record.id}"
    )
    return new_record, False


def batch_get_or_create_files(
    db: Session,
    user_id: int,
    files: list[dict],  # [{rel_path, md5, size, upload_source}, ...]
    business_type: str | None = None,
    business_id: int | None = None,
) -> list[File]:
    """批量登记文件：一次查询 MD5 + original_name，一次 bulk insert

    files: 预计算结果列表，每项包含 rel_path, md5, size, upload_source，可选 mime_type
    注意：调用方必须确保 md5/size 已预计算，本函数不做任何磁盘读取；
    mime_type 缺失时仅用确定性扩展名映射补齐（131），真实类型由修复功能兜底
    """
    if not files:
        return []

    # 1. 批量查询已有 MD5 记录（一次查询）
    all_md5s = [f["md5"] for f in files if f.get("md5")]
    existing_map: dict[str, File] = {}
    if all_md5s:
        existing_records = (
            db.query(File)
            .filter(
                File.user_id == user_id,
                File.md5.in_(all_md5s),
                File.deleted_at.is_(None),
                File.ref_count > 0,
            )
            .all()
        )
        for rec in existing_records:
            existing_map[rec.md5] = rec

    # 2. 批量预查询 original_name 唯一性（避免逐条查询）
    existing_names: set[str] = set()
    if files:
        candidate_names = [os.path.basename(f["rel_path"]) for f in files]
        existing_names = set(
            row[0]
            for row in db.query(File.original_name)
            .filter(
                File.original_name.in_(candidate_names),
                File.deleted_at.is_(None),
            )
            .all()
        )

    # 3. 构建新记录列表
    new_records: list[File] = []
    name_counter: dict[str, int] = {}  # 跟踪同名文件的后缀计数
    reuse_count = 0  # 秒传命中计数
    for info in files:
        md5 = info.get("md5")
        if not md5:
            continue

        existing = existing_map.get(md5)
        original_name = os.path.basename(info["rel_path"])
        base, ext = os.path.splitext(original_name)
        # 131：批量路径禁止磁盘 I/O，仅用确定性扩展名映射补齐（info 可显式传 mime_type）
        info_mime = info.get("mime_type") or mime_type_from_ext(info["rel_path"])

        # 生成唯一名称（批量模式，内存内计算）
        unique_name = original_name
        if original_name in existing_names:
            counter = name_counter.get(original_name, 1)
            while f"{base}_{counter}{ext}" in existing_names:
                counter += 1
            unique_name = f"{base}_{counter}{ext}"
            name_counter[original_name] = counter + 1
        existing_names.add(unique_name)

        if existing:
            # 秒传：复用路径
            new_record = File(
                user_id=user_id,
                md5=md5,
                original_name=unique_name,
                rel_path=existing.rel_path,
                size_bytes=existing.size_bytes,
                # 131：存量记录 mime 为空时用扩展名映射补齐
                mime_type=existing.mime_type or info_mime,
                upload_source=info["upload_source"],
                business_type=business_type,
                business_id=business_id,
                ref_count=1,
                created_at=time.time(),
            )
            existing.ref_count += 1
            reuse_count += 1
        else:
            # 正常上传
            new_record = File(
                user_id=user_id,
                md5=md5,
                original_name=unique_name,
                rel_path=info["rel_path"],
                size_bytes=info.get("size", 0),
                mime_type=info_mime,
                upload_source=info["upload_source"],
                business_type=business_type,
                business_id=business_id,
                ref_count=1,
                created_at=time.time(),
            )
        new_records.append(new_record)

    # 4. 批量插入 + 单次 flush
    if new_records:
        db.add_all(new_records)
        db.flush()

    # 5. 汇总日志
    log.info(
        "批量文件登记完成: total={} reuse={} new={} business={}/{}",
        len(new_records),
        reuse_count,
        len(new_records) - reuse_count,
        business_type,
        business_id,
    )

    return new_records


def repair_file_mime_types(
    db: Session,
    only_empty: bool = True,
    upload_source: str | None = None,
) -> dict:
    """扫描 File 表，按物理文件重新探测并修正 mime_type（Step 116 文件修复功能）

    默认仅处理 mime_type 为空/可疑的记录；可按 upload_source 过滤。
    返回统计：扫描数、修正数、未变数、跳过数（无物理文件）、明细。
    """
    query = db.query(File).filter(File.deleted_at.is_(None))
    if upload_source:
        query = query.filter(File.upload_source == upload_source)
    records = query.all()

    scanned = 0
    repaired = 0
    unchanged = 0
    skipped = 0
    details: list[dict] = []

    for rec in records:
        if only_empty and rec.mime_type:
            continue
        scanned += 1
        abs_path = resolve_safe_path(rec.rel_path)
        if not abs_path or not os.path.isfile(abs_path):
            skipped += 1
            details.append(
                {
                    "id": rec.id,
                    "rel_path": rec.rel_path,
                    "action": "skipped",
                    "reason": "物理文件缺失",
                }
            )
            continue
        detected = detect_mime_type(abs_path, rec.upload_source or "")
        if detected != rec.mime_type:
            details.append(
                {
                    "id": rec.id,
                    "rel_path": rec.rel_path,
                    "action": "repaired",
                    "old": rec.mime_type or "",
                    "new": detected,
                }
            )
            rec.mime_type = detected
            repaired += 1
        else:
            unchanged += 1

    if repaired:
        db.commit()
        log.info(
            "文件 MIME 修复完成",
            scanned=scanned,
            repaired=repaired,
            unchanged=unchanged,
            skipped=skipped,
        )
    return {
        "scanned": scanned,
        "repaired": repaired,
        "unchanged": unchanged,
        "skipped": skipped,
        "details": details,
    }


def ensure_unique_name(db: Session, user_id: int, original_name: str) -> str:
    """检查 original_name 是否已存在（全用户范围，含软删除记录），存在则追加后缀"""
    base, ext = os.path.splitext(original_name)
    candidate = original_name
    counter = 1
    while (
        db.query(File)
        .filter(
            File.original_name == candidate,
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


def soft_delete_file(db: Session, file_record: File) -> bool:
    """软删单条文件记录；引用归零且无其他有效记录共享物理文件时一并删除磁盘文件。

    返回是否物理删除磁盘文件。
    """
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
            removed_disk = safe_unlink(rel_path_to_abs(file_record.rel_path))
    return removed_disk


def decrement_analysis_files(db: Session, analysis) -> int:
    """递减 Analysis 关联的所有文件（含骨架产物）的引用计数"""
    import json

    # 兜底清理残留的中间帧文件（_f*.jpg + _sk*.jpg）
    if analysis.video_url:
        _cleanup_orphan_intermediate_frames(analysis.video_url, analysis.user_id)

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
            log.info(f"清理已删除文件: {record.rel_path}")
        # 删除记录
        db.delete(record)

    return cleaned


def cleanup_orphan_paths(rel_paths: list[str]) -> int:
    """物理删除指定相对路径的文件（不查 DB），返回成功删除的数量"""
    cleaned = 0
    for rel_path in rel_paths:
        abs_path = rel_path_to_abs(rel_path)
        if safe_unlink(abs_path):
            cleaned += 1
            log.info(f"清理孤儿文件: {rel_path}")
    return cleaned


def _cleanup_orphan_intermediate_frames(video_url: str, user_id: int | None = None) -> int:
    """兜底清理残留的中间帧文件（_f*.jpg + _sk*.jpg），返回清理数量"""
    import glob

    abs_path = rel_path_to_abs(video_url)
    video_dir = os.path.dirname(abs_path)
    base = os.path.splitext(os.path.basename(video_url))[0]
    cleaned = 0

    for pattern in [f"{base}_f*.jpg", f"{base}_sk*.jpg"]:
        for path in glob.glob(os.path.join(video_dir, pattern)):
            try:
                os.remove(path)
                cleaned += 1
            except OSError as exc:
                log.warning("兜底清理中间帧失败: %s - %s", path, exc)

    if cleaned:
        log.info("兜底清理中间帧: {} 个文件 video={}", cleaned, video_url)
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
        # videos/ 目录下可能是视频文件，也可能是抽帧图片
        ext = os.path.splitext(rel_path)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
            return "video_frame"
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
                            "usage_status": "orphan",
                            "usage_reason": "磁盘孤儿，未注册到文件表",
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
            log.info(f"文件已注册，跳过: {rel_path}")
            continue

        # 计算 MD5
        md5 = compute_md5_from_path(abs_path)
        size = get_file_size(abs_path)

        # 推断 user_id 和 upload_source
        user_id = _infer_user_id(rel_path) or default_user_id
        upload_source = _infer_upload_source(rel_path)

        original_name = ensure_unique_name(db, user_id, os.path.basename(rel_path))
        record = File(
            user_id=user_id,
            md5=md5 or "",
            original_name=original_name,
            rel_path=rel_path,
            size_bytes=size,
            # 131：孤儿注册同样按物理文件探测 mime（此处已读盘算 MD5）
            mime_type=resolve_mime_type(abs_path, upload_source),
            upload_source=upload_source,
            ref_count=1,
            created_at=time.time(),
        )
        db.add(record)
        registered.append(record)
        log.info(f"注册孤立文件: {rel_path} user_id={user_id} source={upload_source}")

    return registered


def classify_file_usage(db: Session, file_record: File) -> tuple[str, str]:
    """根据业务表实际引用核查，返回 (usage_status, usage_reason)。

    判定顺序（优先级从高到低）：
    1. 已软删 → marked_deleted
    2. 引用计数归零 → unreferenced
    3. 有 business_type + business_id → 按业务类型查对应表做路径匹配
    4. 无 business_id → 按 upload_source 推断应查的业务表做兜底匹配
    5. 以上均不匹配 → unreferenced
    """
    if file_record.deleted_at is not None:
        return "marked_deleted", "已标记删除，待物理清理"
    if file_record.ref_count <= 0:
        return "unreferenced", "引用计数已归零"

    rel = file_record.rel_path
    bt = file_record.business_type
    bid = file_record.business_id
    src = file_record.upload_source
    uid = file_record.user_id

    # 步骤 3：business_type + business_id 精确匹配
    if bt is not None and bid is not None:
        try:
            if bt == "user":
                user = db.query(User).filter(User.id == bid).first()
                if user is not None and user.avatar_url == rel:
                    return "in_use", "用户头像引用有效"
                return "unreferenced", "用户头像引用已失效"

            if bt == "gear":
                gear = db.query(Gear).filter(Gear.id == bid).first()
                if gear is not None and gear.photo == rel:
                    return "in_use", "装备图片引用有效"
                return "unreferenced", "装备记录引用已失效"

            if bt == "analysis":
                analysis = db.query(Analysis).filter(Analysis.id == bid).first()
                if analysis is not None:
                    if analysis.video_url and rel in analysis.video_url:
                        return "in_use", "分析报告引用有效"
                    if analysis.thumb and rel in analysis.thumb:
                        return "in_use", "分析报告引用有效"
                    if analysis.highlights and rel in (analysis.highlights or ""):
                        return "in_use", "分析报告引用有效"
                    if analysis.pose and rel in (analysis.pose or ""):
                        return "in_use", "分析报告引用有效"
                return "unreferenced", "分析报告引用已失效"
        except Exception as exc:
            log.warning("classify_file_usage 业务表查询异常: %s", exc, exc_info=True)
            return "unreferenced", "验证异常"

        if bt:
            return "unreferenced", f"未知业务类型 {bt}"

    # 步骤 4：upload_source 推断兜底（business_type=None 的文件）
    # 不被小程序直接消费的源：原片 / 抽帧帧图，直接判定未引用（可清除）
    if src in NON_CONSUMED_SOURCES:
        return "unreferenced", "原视频/抽帧帧图不被小程序直接消费，可清除"

    if src == "avatar":
        try:
            user = db.query(User).filter(User.id == uid, User.avatar_url == rel).first()
            if user is not None:
                return "in_use", "用户头像引用有效"
            return "unreferenced", "用户头像引用已失效"
        except Exception as exc:
            log.warning("classify_file_usage avatar 查询异常: %s", exc, exc_info=True)
            return "unreferenced", "验证异常"

    if src == "gear_image":
        try:
            gear = db.query(Gear).filter(Gear.user_id == uid, Gear.photo == rel).first()
            if gear is not None:
                return "in_use", "装备图片引用有效"
            return "unreferenced", "装备记录引用已失效"
        except Exception as exc:
            log.warning("classify_file_usage gear_image 查询异常: %s", exc, exc_info=True)
            return "unreferenced", "验证异常"

    # 被消费源（播放短片 / 骨架 / 封面等）：按用户 Analysis 路径匹配兜底
    if src in ANALYSIS_MATCH_SOURCES:
        try:
            analyses = db.query(Analysis).filter(Analysis.user_id == uid).all()
            for a in analyses:
                if a.video_url and rel in a.video_url:
                    return "in_use", "分析报告引用有效"
                if a.thumb and rel in a.thumb:
                    return "in_use", "分析报告引用有效"
                if a.highlights and rel in (a.highlights or ""):
                    return "in_use", "分析报告引用有效"
                if a.pose and rel in (a.pose or ""):
                    return "in_use", "分析报告引用有效"
            return "unreferenced", "分析报告引用已失效"
        except Exception as exc:
            log.warning("classify_file_usage consumed 查询异常: %s", exc, exc_info=True)
            return "unreferenced", "验证异常"

    return "unreferenced", "未绑定业务记录"


def bulk_classify_files(db: Session, files: list[File]) -> dict[int, tuple[str, str]]:
    """批量分类文件状态，预加载业务数据避免 N+1 查询。

    返回 {file_id: (status, reason)}。
    """
    user_ids = set()
    gear_ids = set()
    analysis_ids = set()
    video_user_ids = set()

    for f in files:
        if f.business_type == "user" and f.business_id:
            user_ids.add(f.business_id)
        elif f.business_type == "gear" and f.business_id:
            gear_ids.add(f.business_id)
        elif f.business_type == "analysis" and f.business_id:
            analysis_ids.add(f.business_id)
        if f.upload_source == "avatar":
            user_ids.add(f.user_id)
        if f.upload_source == "gear_image":
            video_user_ids.add(f.user_id)
        if f.upload_source in ANALYSIS_MATCH_SOURCES:
            video_user_ids.add(f.user_id)

    users = (
        {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    )
    gears = (
        {g.id: g for g in db.query(Gear).filter(Gear.id.in_(gear_ids)).all()} if gear_ids else {}
    )
    analyses = (
        {a.id: a for a in db.query(Analysis).filter(Analysis.id.in_(analysis_ids)).all()}
        if analysis_ids
        else {}
    )
    video_analyses: dict[int, list[Analysis]] = {}
    if video_user_ids:
        for a in db.query(Analysis).filter(Analysis.user_id.in_(video_user_ids)).all():
            video_analyses.setdefault(a.user_id, []).append(a)

    def _check_analysis(a: Analysis | None, rel: str) -> bool:
        if a is None:
            return False
        return bool(
            (a.video_url and rel in a.video_url)
            or (a.thumb and rel in a.thumb)
            or (a.highlights and rel in (a.highlights or ""))
            or (a.pose and rel in (a.pose or ""))
        )

    result: dict[int, tuple[str, str]] = {}
    for f in files:
        rel = f.rel_path
        bt = f.business_type
        bid = f.business_id
        src = f.upload_source
        uid = f.user_id

        if f.deleted_at is not None:
            result[f.id] = ("marked_deleted", "已标记删除，待物理清理")
            continue

        if f.ref_count <= 0:
            result[f.id] = ("unreferenced", "引用计数归零")
            continue

        if bt is not None and bid is not None:
            if bt == "user":
                user = users.get(bid)
                if user and user.avatar_url == rel:
                    result[f.id] = ("in_use", "用户头像引用有效")
                else:
                    result[f.id] = ("unreferenced", "用户头像引用已失效")
                continue
            if bt == "gear":
                gear = gears.get(bid)
                if gear and gear.photo == rel:
                    result[f.id] = ("in_use", "装备图片引用有效")
                else:
                    result[f.id] = ("unreferenced", "装备记录引用已失效")
                continue
            if bt == "analysis":
                analysis = analyses.get(bid)
                if _check_analysis(analysis, rel):
                    result[f.id] = ("in_use", "分析报告引用有效")
                else:
                    result[f.id] = ("unreferenced", "分析报告引用已失效")
                continue
            result[f.id] = ("unreferenced", f"未知业务类型 {bt}")
            continue

        if src == "avatar":
            user = users.get(uid)
            if user and user.avatar_url == rel:
                result[f.id] = ("in_use", "用户头像引用有效")
            else:
                result[f.id] = ("unreferenced", "用户头像引用已失效")
            continue

        if src == "gear_image":
            gear_match = any(g.user_id == uid and g.photo == rel for g in gears.values())
            if gear_match:
                result[f.id] = ("in_use", "装备图片引用有效")
            else:
                result[f.id] = ("unreferenced", "装备记录引用已失效")
            continue

        if src in ANALYSIS_MATCH_SOURCES:
            matched = any(_check_analysis(a, rel) for a in video_analyses.get(uid, []))
            if matched:
                result[f.id] = ("in_use", "分析报告引用有效")
            else:
                result[f.id] = ("unreferenced", "分析报告引用已失效")
            continue

        result[f.id] = ("unreferenced", "未绑定业务记录")

    return result
