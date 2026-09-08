"""引用计数服务（138 文件管理重构）

`ref_count` 语义：「受管文件被业务记录引用的次数」，事实来源是 `file_bindings` 表。

- 上传登记时 ref_count = 0（尚未绑定任何业务）
- `bind` 插入一条绑定 → +1（重复 bind 同一目标不重复计数）
- `unbind` 删除一条绑定 → -1
- 归零后不立即软删，交由 `cleanup_unbound` 在宽限期后回收

**仅允许被 `app.services.file_service` 门面调用**。
"""

import time

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.file import File
from app.models.file_binding import FileBinding
from app.services import file_refs

log = get_logger("user")


def find_active(db: Session, user_id: int, rel_path: str) -> File | None:
    """按 (user_id, rel_path) 查找未软删的受管文件"""
    return (
        db.query(File)
        .filter(
            File.user_id == user_id,
            File.rel_path == rel_path,
            File.deleted_at.is_(None),
        )
        .first()
    )


def bindings_of_record(db: Session, business_type: str, business_id: int) -> list[FileBinding]:
    """某条业务记录当前的全部绑定"""
    return (
        db.query(FileBinding)
        .filter(
            FileBinding.business_type == business_type,
            FileBinding.business_id == business_id,
        )
        .all()
    )


def bind(
    db: Session,
    user_id: int,
    rel_path: str,
    business_type: str,
    business_id: int,
    field: str = "",
) -> File | None:
    """业务记录关联一个受管文件：写入绑定并 ref_count + 1

    幂等：同一 (文件, 业务记录, 字段) 重复 bind 不会重复计数。
    文件未登记返回 None。
    """
    if not rel_path:
        return None
    file_record = find_active(db, user_id, rel_path)
    if file_record is None:
        log.warning(
            "引用绑定失败：文件未登记",
            user_id=user_id,
            rel_path=rel_path,
            business_type=business_type,
            business_id=business_id,
        )
        return None

    binding = FileBinding(
        file_id=file_record.id,
        user_id=user_id,
        business_type=business_type,
        business_id=int(business_id),
        field=field,
        created_at=time.time(),
    )
    db.add(binding)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return file_record  # 绑定已存在，计数不变

    if not file_record.business_type and not file_record.business_id:
        file_record.business_type = business_type
        file_record.business_id = int(business_id)
    file_record.ref_count = int(file_record.ref_count or 0) + 1
    return file_record


def unbind(
    db: Session,
    user_id: int,
    rel_path: str,
    business_type: str | None = None,
    business_id: int | None = None,
    field: str | None = None,
) -> bool:
    """业务记录解除对一个受管文件的引用：删除绑定并 ref_count - 1（下限 0）

    归零不立即软删，交由 cleanup_unbound 宽限期回收。
    """
    if not rel_path:
        return False
    file_record = find_active(db, user_id, rel_path)
    if file_record is None:
        return False

    query = db.query(FileBinding).filter(
        FileBinding.file_id == file_record.id,
        FileBinding.user_id == user_id,
    )
    if business_type is not None:
        query = query.filter(FileBinding.business_type == business_type)
    if business_id is not None:
        query = query.filter(FileBinding.business_id == business_id)
    if field is not None:
        query = query.filter(FileBinding.field == field)

    removed = query.delete(synchronize_session=False)
    if not removed:
        return False

    file_record.ref_count = max(0, int(file_record.ref_count or 0) - removed)
    return True


def rebind(
    db: Session,
    user_id: int,
    business_type: str,
    business_id: int,
    new_paths: list[str],
    field: str = "",
) -> dict[str, int]:
    """按目标引用集合做差量重绑（幂等）

    - 新增的路径 → bind(+1)
    - 已移除的路径 → unbind(-1)
    - 未变化的路径 → 不动（重复调用不会重复计数）

    Returns:
        {"bound": n, "unbound": n}
    """
    target = {p for p in new_paths if p}
    current = {
        row[0]
        for row in db.query(File.rel_path)
        .join(FileBinding, FileBinding.file_id == File.id)
        .filter(
            FileBinding.business_type == business_type,
            FileBinding.business_id == business_id,
        )
        .all()
    }
    if target == current:
        return {"bound": 0, "unbound": 0}

    for path in current - target:
        unbind(db, user_id, path, business_type, business_id, field)
    for path in target - current:
        bind(db, user_id, path, business_type, business_id, field)
    return {"bound": len(target - current), "unbound": len(current - target)}


def unbind_record(db: Session, business_type: str, business_id: int) -> int:
    """解除某条业务记录引用的全部文件（删除业务记录时调用）"""
    bindings = bindings_of_record(db, business_type, business_id)
    if not bindings:
        return 0

    released = 0
    for binding in bindings:
        file_record = db.query(File).filter(File.id == binding.file_id).first()
        db.delete(binding)
        if file_record is not None:
            file_record.ref_count = max(0, int(file_record.ref_count or 0) - 1)
            released += 1
    return released


def bound_rel_paths(db: Session, user_id: int | None = None) -> set[str]:
    """已被业务绑定的相对路径集合（宽限期回收时用于兜底保护）"""
    query = db.query(File.rel_path).join(FileBinding, FileBinding.file_id == File.id)
    if user_id is not None:
        query = query.filter(File.user_id == user_id)
    return {row[0] for row in query.all()}


def cleanup_unbound(db: Session, grace_hours: int = 24) -> int:
    """回收「从未绑定业务」的临时文件

    判定：ref_count <= 0、未软删、创建时间早于宽限期，且未被绑定表或业务表引用。
    返回软删的文件数量。
    """
    cutoff = time.time() - grace_hours * 3600
    candidates = (
        db.query(File)
        .filter(
            File.deleted_at.is_(None),
            File.ref_count <= 0,
            File.created_at > 0,
            File.created_at < cutoff,
        )
        .all()
    )
    if not candidates:
        return 0

    protected = bound_rel_paths(db) | set(file_refs.collect_business_refs(db).keys())
    cleaned = 0
    for record in candidates:
        if record.rel_path in protected:
            continue
        record.deleted_at = time.time()
        cleaned += 1

    if cleaned:
        log.info("回收未绑定文件: count={} grace_hours={}", cleaned, grace_hours)
    return cleaned


def purge_bindings_of_file(db: Session, file_id: int) -> int:
    """删除某文件的全部绑定（软删文件时使用）"""
    result = db.execute(
        delete(FileBinding).where(FileBinding.file_id == file_id),
    )
    return int(result.rowcount or 0)
