"""文件服务层：后端文件操作的**唯一对外门面**（138 文件管理重构）

路由层与其它 service 只允许 `from app.services import file_service` 后调用本模块的
统一工具方法，禁止自行拼 uploads 路径、自造文件名、直接写盘、直接改 ref_count
或直接操作 File 模型（见 tests/test_file_architecture.py 守卫测试）。

内部分工：
- `file_store`：物理存储（MD5 命名、路径推导、写盘/删盘、MIME 兜底）
- `file_refs`：业务引用注册表（哪些表哪些字段引用受管文件）
- `file_ref_service`：引用计数的唯一变更实现

下方「统一门面 API」之前的函数均为改造期保留的旧实现，C7 全量替换后删除。
"""

import os
import time
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.file import File
from app.services import file_ref_service, file_refs, file_store

log = get_logger("user")

# 文件使用边界（118 §5.8）：小程序实际消费判定
# 原片 / 抽帧帧图不被小程序直接消费，可直接清除（unreferenced）


def repair_file_mime_types(
    db: Session,
    only_empty: bool = True,
    upload_source: str | None = None,
) -> dict:
    """扫描 File 表，按物理文件重新探测并修正 mime_type

    默认仅处理 mime_type 为空的记录；可按 upload_source 过滤。
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
        if not file_store.exists(rec.rel_path):
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
        detected = file_store.mime_of(file_store.abs_of(rec.rel_path), rec.upload_source or "")
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


def cleanup_expired(db: Session, days: int = 30) -> int:
    """物理清理已软删超过 N 天的文件及其记录，返回清理数量"""
    cutoff = time.time() - (days * 86400)
    expired = db.query(File).filter(File.deleted_at.isnot(None), File.deleted_at < cutoff).all()

    cleaned = 0
    for record in expired:
        if file_store.unlink(record.rel_path):
            cleaned += 1
            log.info("清理已删除文件: %s", record.rel_path)
        db.delete(record)
    return cleaned


# ==================== 统一门面 API（138：后端文件操作唯一入口） ====================


@dataclass
class FileDraft:
    """批量登记入参（预计算 md5/size 可做到零额外磁盘 I/O）"""

    rel_path: str = ""  # 已落盘产物的受管相对路径（可选，仅作后缀推断兜底）
    src_path: str = ""  # 临时产物绝对路径（自动迁入受管路径）
    md5: str = ""  # 已知 MD5（留空则按需计算）
    size: int = 0  # 已知大小（留空则按需探测）
    ext: str = ""  # 后缀（留空则取 original_name / rel_path 的后缀）
    upload_source: str = ""  # avatar/gear_image/video/skeleton_video/...
    original_name: str = ""
    mime_type: str = ""


def _materialize(rel_path: str, content: bytes | None, src_path: str | None) -> None:
    """把内容落到受管路径：优先直接写内容，否则把临时文件迁移进去"""
    abs_path = file_store.abs_of(rel_path)
    if content is not None:
        file_store.write_bytes(abs_path, content)
    elif src_path and os.path.abspath(src_path) != abs_path:
        file_store.move_into_place(src_path, abs_path)


def _is_same_path(src_path: str | None, target_abs: str) -> bool:
    """源路径与目标路径是否同一文件（避免把目标文件当临时文件删掉）"""
    return bool(src_path) and os.path.abspath(str(src_path)) == os.path.abspath(target_abs)


def _drop_duplicate_src(src_path: str, managed_rel_path: str) -> None:
    """批量登记命中去重时删除重复的中间产物（与受管文件同址时保留）"""
    if not src_path:
        return
    if _is_same_path(src_path, file_store.abs_of(managed_rel_path)):
        return
    file_store.unlink_abs(src_path)


def _resolve_ext(ext: str, original_name: str, rel_path: str) -> str:
    """后缀优先级：显式 ext > original_name > 既有 rel_path"""
    if ext:
        return ext
    for candidate in (original_name, rel_path):
        suffix = os.path.splitext(candidate)[1]
        if suffix:
            return suffix
    return ""


def _new_file_record(
    user_id: int,
    md5: str,
    rel_path: str,
    upload_source: str,
    original_name: str,
    size_bytes: int,
    mime_type: str,
    business: tuple[str, int] | None,
    security_checked: bool | None,
) -> File:
    """构造一条未落库的 File 记录（登记的唯一构造入口）

    引用计数一律从 0 起：绑定由 `bind` 写入 file_bindings 后再 +1，
    保证「计数」与「绑定事实」始终一致。
    """
    business_type, business_id = business if business else (None, None)
    return File(
        user_id=user_id,
        md5=md5,
        original_name=original_name,
        rel_path=rel_path,
        size_bytes=size_bytes,
        mime_type=mime_type,
        upload_source=upload_source,
        business_type=business_type,
        business_id=business_id,
        ref_count=0,
        security_checked=1 if security_checked else 0,
        created_at=time.time(),
    )


def _bind_business(
    db: Session,
    user_id: int,
    rel_path: str,
    business: tuple[str, int] | None,
) -> None:
    """登记后按 business 完成绑定（写入 file_bindings 并 ref_count +1）"""
    if not business:
        return
    bind(db, user_id, rel_path, business[0], business[1])


# -------------------- 登记 --------------------


def register(
    db: Session,
    user_id: int,
    *,
    content: bytes | None = None,
    src_path: str | None = None,
    category: str = "",
    original_name: str = "",
    ext: str = "",
    mime_type: str = "",
    security_checked: bool | None = None,
    business: tuple[str, int] | None = None,
) -> tuple[File, bool]:
    """登记一个受管文件：写盘 + 落库（同一用户同一 MD5 只保留一条记录）

    Args:
        content: 内存内容（与 src_path 二选一）
        src_path: 临时文件绝对路径（自动迁入受管路径）
        category: 分类目录键（同时作为 upload_source），如 avatar / gear_image / video
        business: (business_type, business_id)，传入时同步完成引用绑定（ref_count=1）

    Returns:
        (File 记录, 是否复用了已有记录/物理文件)
    """
    if content is None and not src_path:
        raise ValueError("register 需要 content 或 src_path 之一")

    if content is not None:
        md5 = file_store.md5_of(content=content)
        size_bytes = len(content)
    else:
        md5, size_bytes = file_store.md5_and_size_of(str(src_path))
    if not md5:
        raise ValueError(f"无法计算 MD5: src_path={src_path}")

    upload_source = category or file_store.DEFAULT_CATEGORY
    resolved_ext = _resolve_ext(ext, original_name, "")
    rel_path = file_store.build_rel_path(user_id, md5, resolved_ext, upload_source)

    existing = find_by_md5(db, user_id, md5)
    if existing is not None:
        if not file_store.exists(existing.rel_path):
            _materialize(existing.rel_path, content, src_path)
        elif not _is_same_path(src_path, file_store.abs_of(existing.rel_path)):
            file_store.unlink_abs(str(src_path))
        if security_checked:
            existing.security_checked = 1
        if not existing.mime_type:
            existing.mime_type = file_store.mime_of(
                file_store.abs_of(existing.rel_path), upload_source, mime_type
            )
        _bind_business(db, user_id, existing.rel_path, business)
        log.info(
            "登记复用已有文件: md5={} rel_path={} file_id={}",
            md5[:12],
            existing.rel_path,
            existing.id,
        )
        return existing, True

    if not file_store.exists(rel_path):
        _materialize(rel_path, content, src_path)
    elif not _is_same_path(src_path, file_store.abs_of(rel_path)):
        file_store.unlink_abs(str(src_path))

    resolved_mime = file_store.mime_of(file_store.abs_of(rel_path), upload_source, mime_type)
    record = _new_file_record(
        user_id=user_id,
        md5=md5,
        rel_path=rel_path,
        upload_source=upload_source,
        original_name=original_name,
        size_bytes=size_bytes,
        mime_type=resolved_mime,
        business=business,
        security_checked=security_checked,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = find_by_md5(db, user_id, md5)
        if existing is not None:
            _bind_business(db, user_id, existing.rel_path, business)
            return existing, True
        raise
    _bind_business(db, user_id, rel_path, business)
    log.info(
        "登记新文件: md5={} rel_path={} source={} file_id={}",
        md5[:12],
        rel_path,
        upload_source,
        record.id,
    )
    return record, False


def register_batch(
    db: Session,
    user_id: int,
    items: list[FileDraft],
    business: tuple[str, int] | None = None,
) -> list[File]:
    """批量登记受管文件（预计算 md5/size 时零额外磁盘 I/O + 单批 flush）

    同一批内相同 MD5 只落一条记录；返回与入参顺序一致（去重项复用同一记录）。
    """
    if not items:
        return []

    md5s = [item.md5 for item in items if item.md5]
    existing_map: dict[str, File] = {}
    if md5s:
        for record in (
            db.query(File)
            .filter(
                File.user_id == user_id,
                File.md5.in_(md5s),
                File.deleted_at.is_(None),
            )
            .all()
        ):
            existing_map[record.md5] = record

    created: dict[str, File] = {}
    results: list[File] = []
    for item in items:
        md5 = item.md5 or file_store.md5_of(path=item.src_path or None)
        if not md5:
            log.warning("批量登记跳过无 MD5 的项: %s", item.rel_path or item.src_path)
            continue

        existing = existing_map.get(md5)
        if existing is not None:
            # 内容已登记：源文件内容重复，删除中间产物避免残留
            _drop_duplicate_src(item.src_path, existing.rel_path)
            _bind_business(db, user_id, existing.rel_path, business)
            results.append(existing)
            continue

        if md5 in created:
            _drop_duplicate_src(item.src_path, created[md5].rel_path)
            results.append(created[md5])
            continue

        upload_source = item.upload_source or file_store.DEFAULT_CATEGORY
        resolved_ext = _resolve_ext(item.ext, item.original_name, item.rel_path)
        rel_path = file_store.build_rel_path(user_id, md5, resolved_ext, upload_source)

        if item.src_path and file_store.abs_of(rel_path) != os.path.abspath(item.src_path):
            file_store.move_into_place(item.src_path, file_store.abs_of(rel_path))

        size_bytes = item.size or file_store.size_of(rel_path)
        record = _new_file_record(
            user_id=user_id,
            md5=md5,
            rel_path=rel_path,
            upload_source=upload_source,
            original_name=item.original_name,
            size_bytes=size_bytes,
            mime_type=file_store.mime_of(
                file_store.abs_of(rel_path), upload_source, item.mime_type, probe=False
            ),
            business=business,
            security_checked=None,
        )
        db.add(record)
        created[md5] = record
        results.append(record)

    if created:
        db.flush()
        if business:
            for record in created.values():
                _bind_business(db, user_id, record.rel_path, business)

    log.info(
        "批量登记完成: total={} reused={} new={} business={}",
        len(results),
        len(results) - len(created),
        len(created),
        business,
    )
    return results


# -------------------- 引用计数（唯一变更入口） --------------------


def bind(
    db: Session,
    user_id: int,
    rel_path: str,
    business_type: str,
    business_id: int,
    field: str = "",
):
    """业务记录关联受管文件：写入绑定并 ref_count + 1（幂等）"""
    return file_ref_service.bind(db, user_id, rel_path, business_type, business_id, field)


def unbind(
    db: Session,
    user_id: int,
    rel_path: str,
    business_type: str | None = None,
    business_id: int | None = None,
    field: str | None = None,
) -> bool:
    """业务记录解除关联：删除绑定并 ref_count - 1"""
    return file_ref_service.unbind(db, user_id, rel_path, business_type, business_id, field)


def rebind(
    db: Session,
    user_id: int,
    business_type: str,
    business_id: int,
    new_paths: list[str],
    field: str = "",
) -> dict[str, int]:
    """按目标引用集合做差量重绑（幂等，换图场景）"""
    return file_ref_service.rebind(db, user_id, business_type, business_id, new_paths, field)


def unbind_record(db: Session, business_type: str, business_id: int) -> int:
    """解除某条业务记录引用的全部文件（删除业务记录时调用）"""
    return file_ref_service.unbind_record(db, business_type, business_id)


# -------------------- 路径与元数据 --------------------


def build_rel_path(user_id: int, md5: str, ext: str, category: str) -> str:
    """生成受管相对路径：`{目录}/{user_id}/{md5}.{后缀}`"""
    return file_store.build_rel_path(user_id, md5, ext, category)


def resolve(rel_path: str) -> str | None:
    """相对路径 → 绝对路径，越界返回 None"""
    return file_store.resolve(rel_path)


def abs_of(rel_path: str) -> str:
    """相对路径 → 绝对路径"""
    return file_store.abs_of(rel_path)


def rel_of(abs_path: str) -> str:
    """绝对路径 → 相对路径"""
    return file_store.rel_of(abs_path)


def exists(rel_path: str) -> bool:
    """受管文件是否存在"""
    return file_store.exists(rel_path)


def size_of(rel_path: str) -> int:
    """受管文件大小（字节）"""
    return file_store.size_of(rel_path)


def md5_of(content: bytes | None = None, path: str | None = None) -> str | None:
    """计算 MD5（content 或 path 二选一）"""
    return file_store.md5_of(content=content, path=path)


def mime_of(
    rel_path: str,
    upload_source: str = "",
    mime_type: str = "",
    probe: bool = True,
) -> str:
    """补齐/探测 MIME（probe=False 时零磁盘 I/O，仅扩展名映射）"""
    return file_store.mime_of(
        abs_of(rel_path) if rel_path else None,
        upload_source,
        mime_type,
        probe,
    )


def find_by_md5(db: Session, user_id: int, md5: str) -> File | None:
    """按 (user_id, md5) 查找未软删的受管文件"""
    return (
        db.query(File)
        .filter(File.user_id == user_id, File.md5 == md5, File.deleted_at.is_(None))
        .first()
    )


# -------------------- 查询 / 扫描 --------------------


def owned_by(db: Session, user_id: int, rel_path: str) -> bool:
    """文件是否属于该用户（未软删即可，不再要求 ref_count > 0）"""
    return (
        db.query(File.id)
        .filter(
            File.user_id == user_id,
            File.rel_path == rel_path,
            File.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def collect_business_refs(db: Session, user_id: int | None = None):
    """收集业务表引用的受管路径：{rel_path: [BusinessRef, ...]}"""
    return file_refs.collect_business_refs(db, user_id)


def get_by_id(db: Session, file_id: int) -> File | None:
    """按主键查询文件记录（含已软删）"""
    return db.query(File).filter(File.id == file_id).first()


def query_files(
    db: Session,
    *,
    user_id: int | None = None,
    upload_source: str | None = None,
    business_type: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> list[File]:
    """受管文件列表查询（仅未软删，按创建时间倒序）"""
    query = db.query(File).filter(File.deleted_at.is_(None))
    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    if upload_source:
        query = query.filter(File.upload_source == upload_source)
    if business_type:
        query = query.filter(File.business_type == business_type)
    query = query.order_by(File.created_at.desc())
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def count_files(
    db: Session,
    *,
    user_id: int | None = None,
    upload_source: str | None = None,
    business_type: str | None = None,
) -> int:
    """受管文件计数（仅未软删）"""
    query = db.query(File).filter(File.deleted_at.is_(None))
    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    if upload_source:
        query = query.filter(File.upload_source == upload_source)
    if business_type:
        query = query.filter(File.business_type == business_type)
    return query.count()


def count_deleted(db: Session) -> int:
    """已软删（待物理清理）的文件记录数"""
    return db.query(File).filter(File.deleted_at.isnot(None)).count()


def source_stats(db: Session) -> dict[str, dict]:
    """按 upload_source 分组统计 {source: {count, size_bytes}}"""
    from sqlalchemy import func

    rows = (
        db.query(File.upload_source, func.count(File.id), func.sum(File.size_bytes))
        .filter(File.deleted_at.is_(None))
        .group_by(File.upload_source)
        .all()
    )
    return {source: {"count": count, "size_bytes": size or 0} for source, count, size in rows}


def total_size(db: Session) -> int:
    """受管文件总大小（字节）"""
    from sqlalchemy import func

    return db.query(func.sum(File.size_bytes)).filter(File.deleted_at.is_(None)).scalar() or 0


def classify(db: Session, records: list[File]) -> dict[int, tuple[str, str]]:
    """按业务引用注册表判定每条记录的使用状态：{file_id: (status, reason)}

    与 scan() 共用同一套判定口径（in_use / unreferenced / missing / marked_deleted）。
    """
    referenced = set(file_refs.collect_business_refs(db).keys()) | file_ref_service.bound_rel_paths(
        db
    )
    result: dict[int, tuple[str, str]] = {}
    for record in records:
        if record.deleted_at is not None:
            result[record.id] = ("marked_deleted", "已标记删除，待物理清理")
        elif not file_store.exists(record.rel_path):
            result[record.id] = ("missing", "已登记但物理文件缺失")
        elif record.rel_path in referenced:
            result[record.id] = ("in_use", "业务记录引用有效")
        else:
            result[record.id] = ("unreferenced", "无任何业务记录引用")
    return result


def cleanup_intermediates(user_id: int) -> int:
    """兜底清理用户视频目录下的中间产物（`*_f*.jpg` 抽样帧 / `*_sk*.jpg` 骨架帧）

    受管文件已按 {md5} 命名，不会命中这两个通配；仅清理登记后残留的临时产物。
    """
    import glob

    video_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), "videos", str(user_id))
    if not os.path.isdir(video_dir):
        return 0
    cleaned = 0
    for pattern in ("*_f*.jpg", "*_sk*.jpg"):
        for path in glob.glob(os.path.join(video_dir, pattern)):
            try:
                os.remove(path)
                cleaned += 1
            except OSError as exc:
                log.warning("删除中间帧失败: %s - %s", path, exc)
    if cleaned:
        log.info("兜底清理中间帧: {} 个文件 user_id={}", cleaned, user_id)
    return cleaned


def cleanup_paths(rel_paths: list[str]) -> int:
    """物理删除若干相对路径的文件（孤儿/未登记文件），返回成功数量"""
    cleaned = 0
    for rel_path in rel_paths:
        if unlink(rel_path):
            cleaned += 1
    return cleaned


def register_orphans(
    db: Session,
    rel_paths: list[str],
    default_user_id: int = 0,
) -> list[File]:
    """把磁盘孤儿登记为受管文件（物理文件迁入 {分类}/{user_id}/{md5}.{后缀}）"""
    from app.services.file_store import infer_source, infer_user_id

    registered: list[File] = []
    for rel_path in rel_paths:
        if not file_store.exists(rel_path):
            log.warning("孤儿文件不存在，跳过登记: %s", rel_path)
            continue
        user_id = infer_user_id(rel_path) or default_user_id
        source = infer_source(rel_path)
        record, _ = register(
            db,
            user_id,
            src_path=file_store.abs_of(rel_path),
            category=source,
            original_name=os.path.basename(rel_path),
            ext=os.path.splitext(rel_path)[1],
        )
        registered.append(record)
    if registered:
        db.flush()
    return registered


SCAN_STATUSES = (
    "in_use",  # 已登记且被业务引用
    "unreferenced",  # 已登记但无业务引用
    "missing",  # 已登记但物理文件缺失
    "orphan",  # 磁盘有文件但未登记
    "unregistered_ref",  # 业务引用了未登记的路径
    "marked_deleted",  # 已软删，待物理清理
)

_SKIP_SCAN_DIRS = {"check_tmp", "backups"}


def _walk_upload_dir() -> dict[str, float]:
    """遍历 UPLOAD_DIR，返回 {rel_path: mtime}"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    if not os.path.isdir(upload_dir):
        return {}
    found: dict[str, float] = {}
    for root, dirs, files in os.walk(upload_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_SCAN_DIRS]
        for filename in files:
            abs_path = os.path.join(root, filename)
            rel = file_store.rel_of(abs_path)
            try:
                found[rel] = os.stat(abs_path).st_mtime
            except (OSError, ValueError) as exc:
                log.warning("扫描文件失败: %s", exc)
    return found


def scan(db: Session, user_id: int | None = None) -> dict:
    """扫描受管文件与磁盘，基于业务引用注册表输出五态分类

    五态：in_use / unreferenced / missing / orphan / unregistered_ref
    （另含 marked_deleted 供管理端展示软删记录）

    Returns:
        {total_files, registered_files, status_counts, items}
    """
    business_refs = file_refs.collect_business_refs(db, user_id)
    referenced = set(business_refs.keys()) | file_ref_service.bound_rel_paths(db, user_id)

    query = db.query(File).filter(File.deleted_at.is_(None))
    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    records = query.all()

    status_counts = dict.fromkeys(SCAN_STATUSES, 0)
    items: list[dict] = []
    registered: set[str] = set()

    for record in records:
        registered.add(record.rel_path)
        refs = [
            {
                "business_type": ref.business_type,
                "business_id": ref.business_id,
                "field": ref.field,
            }
            for ref in business_refs.get(record.rel_path, [])
        ]
        if not file_store.exists(record.rel_path):
            status, reason = "missing", "已登记但物理文件缺失"
        elif record.rel_path in referenced:
            status, reason = "in_use", "业务记录引用有效"
        else:
            status, reason = "unreferenced", "无任何业务记录引用"
        status_counts[status] += 1
        items.append(
            {
                "rel_path": record.rel_path,
                "status": status,
                "reason": reason,
                "file_id": record.id,
                "user_id": record.user_id,
                "size_bytes": record.size_bytes or 0,
                "mime_type": record.mime_type or "",
                "upload_source": record.upload_source or "",
                "ref_count": record.ref_count or 0,
                "business_refs": refs,
                "modified_at": 0,
            }
        )

    disk_files = _walk_upload_dir()
    if user_id is not None:
        disk_files = {
            path: mtime
            for path, mtime in disk_files.items()
            if file_store.infer_user_id(path) == user_id
        }

    for rel_path, mtime in sorted(disk_files.items()):
        if rel_path in registered:
            continue
        if rel_path in referenced:
            status, reason = "unregistered_ref", "业务记录引用了未登记的文件"
        else:
            status, reason = "orphan", "磁盘孤儿，未注册到文件表"
        status_counts[status] += 1
        items.append(
            {
                "rel_path": rel_path,
                "status": status,
                "reason": reason,
                "file_id": None,
                "user_id": file_store.infer_user_id(rel_path) or 0,
                "size_bytes": file_store.size_of(rel_path),
                "mime_type": "",
                "upload_source": file_store.infer_source(rel_path),
                "ref_count": 0,
                "business_refs": [
                    {
                        "business_type": ref.business_type,
                        "business_id": ref.business_id,
                        "field": ref.field,
                    }
                    for ref in business_refs.get(rel_path, [])
                ],
                "modified_at": mtime,
            }
        )

    for rel_path in sorted(referenced - registered - set(disk_files)):
        status_counts["unregistered_ref"] += 1
        items.append(
            {
                "rel_path": rel_path,
                "status": "unregistered_ref",
                "reason": "业务记录引用但未登记且文件缺失",
                "file_id": None,
                "user_id": file_store.infer_user_id(rel_path) or 0,
                "size_bytes": 0,
                "mime_type": "",
                "upload_source": file_store.infer_source(rel_path),
                "ref_count": 0,
                "business_refs": [
                    {
                        "business_type": ref.business_type,
                        "business_id": ref.business_id,
                        "field": ref.field,
                    }
                    for ref in business_refs.get(rel_path, [])
                ],
                "modified_at": 0,
            }
        )

    return {
        "total_files": len(disk_files),
        "registered_files": len(records),
        "status_counts": status_counts,
        "items": items,
    }


# -------------------- 删除与回收 --------------------


def soft_delete(db: Session, file_id: int) -> bool:
    """软删单个受管文件（解绑全部业务引用 + 归零 + 删除物理文件）

    受管路径含 user_id 分段，不存在跨用户共享，可直接物理删除。
    """
    record = db.query(File).filter(File.id == file_id, File.deleted_at.is_(None)).first()
    if record is None:
        return False
    file_ref_service.purge_bindings_of_file(db, file_id)
    record.ref_count = 0
    record.deleted_at = time.time()
    file_store.unlink(record.rel_path)
    return True


def soft_delete_batch(db: Session, file_ids: list[int]) -> dict:
    """批量软删受管文件，返回 {"deleted": n, "missing": n, "disk_removed": n}"""
    deleted = 0
    missing = 0
    disk_removed = 0
    missing_ids: list[str] = []
    for file_id in file_ids:
        record = db.query(File).filter(File.id == int(file_id), File.deleted_at.is_(None)).first()
        if record is None:
            missing += 1
            missing_ids.append(str(file_id))
            continue
        file_ref_service.purge_bindings_of_file(db, int(file_id))
        record.ref_count = 0
        record.deleted_at = time.time()
        if file_store.unlink(record.rel_path):
            disk_removed += 1
        deleted += 1
    return {
        "deleted": deleted,
        "missing": missing,
        "disk_removed": disk_removed,
        "missing_ids": missing_ids,
    }


def write_temp(content: bytes, ext: str = "") -> str:
    """写临时文件（如「仅检即弃」的安全检查），返回绝对路径；不进文件表"""
    return file_store.write_temp(content, ext)


def write_bytes(abs_path: str, content: bytes) -> None:
    """把中间产物写到指定绝对路径（骨架帧/抽帧等）

    仅用于「生成后需要立即被 ffmpeg/编码器消费」的中间产物；
    最终纳入管理仍须调用 register / register_batch 完成登记与重命名。
    """
    file_store.write_bytes(abs_path, content)


def md5_and_size_of(path: str) -> tuple[str | None, int]:
    """一次读盘同时得到 MD5 与大小（预计算用）"""
    return file_store.md5_and_size_of(path)


def unlink_abs(abs_path: str) -> bool:
    """删除任意绝对路径的临时文件"""
    return file_store.unlink_abs(abs_path)


def unlink(rel_path: str) -> bool:
    """删除受管文件（仅物理删除，记录状态由 soft_delete 管理）"""
    return file_store.unlink(rel_path)


def mark_security_checked(db: Session, user_id: int, rel_path: str, passed: bool = True) -> bool:
    """标记内容安全检查结果（上传后异步检查完成时调用）"""
    record = (
        db.query(File)
        .filter(
            File.user_id == user_id,
            File.rel_path == rel_path,
            File.deleted_at.is_(None),
        )
        .first()
    )
    if record is None:
        return False
    record.security_checked = 1 if passed else 0
    return True


def cleanup(db: Session, days: int = 30) -> int:
    """物理清理已软删超过 N 天的文件，返回清理数量"""
    return cleanup_expired(db, days)


def cleanup_unbound(db: Session, grace_hours: int = 24) -> int:
    """回收宽限期内从未绑定业务的临时文件"""
    return file_ref_service.cleanup_unbound(db, grace_hours)


# -------------------- 存量迁移 --------------------


def _rewrite_business_path(db: Session, old_path: str, new_path: str) -> int:
    """把业务表中所有引用 old_path 的字段改写为 new_path，返回改写字段数"""
    updated = 0
    for spec in file_refs.FILE_REF_SPECS:
        model = spec.model()
        for extractor in spec.extractors:
            column = getattr(model, extractor.column)
            rows = db.query(model).filter(column.contains(old_path)).all()
            for row in rows:
                value = getattr(row, extractor.column)
                if not isinstance(value, str) or old_path not in value:
                    continue
                if extractor.kind == "column":
                    if value != old_path:
                        continue
                    setattr(row, extractor.column, new_path)
                else:
                    setattr(row, extractor.column, value.replace(old_path, new_path))
                updated += 1
    return updated


def migrate_to_md5(db: Session, dry_run: bool = True) -> dict:
    """存量文件迁移至 MD5 命名 + 单记录（支持预演）

    步骤：
    1. 逐条扫描未软删的 File 记录，推导目标路径 `{分类}/{user_id}/{md5}.{后缀}`
    2. 与当前路径一致 → already_named（幂等）；物理文件缺失 → missing_files
    3. 目标已存在且内容相同 → 复用（删除源文件）；内容不同 → conflicts（不覆盖）
    4. 移动物理文件 + 更新 rel_path + 回填业务表旧路径
    5. 合并同一 (user_id, md5) 的重复记录（保留 id 最小者，ref_count 求和）
    """
    report: dict = {
        "dry_run": dry_run,
        "scanned": 0,
        "renamed": 0,
        "already_named": 0,
        "reused": 0,
        "records_updated": 0,
        "business_updated": 0,
        "duplicates_merged": 0,
        "conflicts": [],
        "missing_files": [],
    }

    records = db.query(File).filter(File.deleted_at.is_(None)).order_by(File.id).all()
    report["scanned"] = len(records)

    for record in records:
        old_rel = record.rel_path
        if not file_store.exists(old_rel):
            report["missing_files"].append(old_rel)
            continue

        md5 = record.md5 or file_store.md5_of(path=file_store.abs_of(old_rel))
        if not md5:
            report["missing_files"].append(old_rel)
            continue

        category = file_store.category_of(record.upload_source or "")
        ext = os.path.splitext(old_rel)[1]
        new_rel = file_store.build_rel_path(record.user_id, md5, ext, category)

        if new_rel == old_rel:
            report["already_named"] += 1
            continue

        old_abs = file_store.abs_of(old_rel)
        new_abs = file_store.abs_of(new_rel)

        if os.path.isfile(new_abs):
            if file_store.md5_of(path=new_abs) == md5:
                report["reused"] += 1
                if not dry_run:
                    file_store.unlink(old_rel)
                    _rewrite_business_path(db, old_rel, new_rel)
                    record.rel_path = new_rel
                    record.md5 = md5
                    report["records_updated"] += 1
                continue
            report["conflicts"].append({"from": old_rel, "to": new_rel, "md5": md5})
            continue

        report["renamed"] += 1
        if dry_run:
            continue

        file_store.move_into_place(old_abs, new_abs)
        report["business_updated"] += _rewrite_business_path(db, old_rel, new_rel)
        record.rel_path = new_rel
        record.md5 = md5
        report["records_updated"] += 1

    report["duplicates_merged"] = _merge_duplicate_records(db, dry_run)
    if not dry_run:
        db.flush()
        log.info("存量文件迁移完成: %s", {k: v for k, v in report.items() if k != "conflicts"})
    return report


def _merge_duplicate_records(db: Session, dry_run: bool) -> int:
    """合并同一 (user_id, md5) 的重复有效记录：保留 id 最小者，ref_count 求和"""
    rows = (
        db.query(File)
        .filter(File.deleted_at.is_(None))
        .order_by(File.user_id, File.md5, File.id)
        .all()
    )
    grouped: dict[tuple[int, str], list[File]] = {}
    for record in rows:
        grouped.setdefault((record.user_id, record.md5), []).append(record)

    merged = 0
    for (_user_id, _md5), group in grouped.items():
        if len(group) < 2:
            continue
        keeper = group[0]
        total_ref = sum(int(r.ref_count or 0) for r in group)
        for duplicate in group[1:]:
            if not dry_run:
                file_ref_service.purge_bindings_of_file(db, duplicate.id)
                duplicate.ref_count = 0
                duplicate.deleted_at = time.time()
            merged += 1
        if not dry_run:
            keeper.ref_count = total_ref
    return merged
