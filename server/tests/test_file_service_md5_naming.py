"""C2/C3 受管文件登记：MD5 命名 + 同用户单记录

- 物理文件名统一 `{md5}.{后缀}`，存于 `uploads/{分类}/{user_id}/`
- 同一用户同一 MD5 只保留一条 File 记录
- 软删后重新上传可再次落库（部分唯一索引排除软删行）
"""

import hashlib
import os

import pytest

from app.models.file import File
from app.services import file_service

pytestmark = pytest.mark.fast


def _md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def _physical_names(user_id: int, category_dir: str) -> list[str]:
    from app.core.config import settings

    target = os.path.join(str(settings.UPLOAD_DIR), category_dir, str(user_id))
    if not os.path.isdir(target):
        return []
    return sorted(os.listdir(target))


# ==================== C2：MD5 命名 ====================


def test_build_rel_path_uses_md5():
    """路径格式固定为 {分类目录}/{user_id}/{md5}.{后缀}"""
    a, b, c = "a" * 32, "b" * 32, "c" * 32
    assert file_service.build_rel_path(7, a, ".jpg", "avatar") == f"avatars/7/{a}.jpg"
    assert file_service.build_rel_path(7, b, "png", "gear_image") == f"gears/7/{b}.png"
    assert file_service.build_rel_path(7, c, ".mp4", "video") == f"videos/7/{c}.mp4"


def test_register_names_file_by_md5(test_db):
    """上传内容按 MD5 命名落盘"""
    content = b"hello-tennis-diary"
    record, reused = file_service.register(
        test_db, 1, content=content, category="gear_image", original_name="my.jpg", ext=".jpg"
    )
    test_db.commit()
    assert reused is False
    assert record.rel_path == f"gears/1/{_md5(content)}.jpg"
    assert file_service.exists(record.rel_path)
    with open(file_service.abs_of(record.rel_path), "rb") as f:
        assert f.read() == content


def test_register_ext_falls_back_to_original_name(test_db):
    """未显式传 ext 时从原始文件名取后缀"""
    content = b"ext-fallback"
    record, _ = file_service.register(
        test_db, 1, content=content, category="avatar", original_name="photo.PNG"
    )
    assert record.rel_path.endswith(".png")


def test_register_src_path_moves_file_into_place(test_db, tmp_path):
    """临时产物路径登记后迁入受管路径，临时文件不再存在"""
    src = tmp_path / "tmp_skeleton.mp4"
    src.write_bytes(b"skeleton-bytes")
    record, reused = file_service.register(
        test_db, 3, src_path=str(src), category="skeleton_video", ext=".mp4"
    )
    assert reused is False
    assert record.rel_path == f"videos/3/{_md5(b'skeleton-bytes')}.mp4"
    assert file_service.exists(record.rel_path)
    assert not src.exists()


def test_register_reuses_existing_physical_file(test_db):
    """同用户重复上传同一内容：不产生第二个物理文件"""
    content = b"duplicate-content"
    first, _ = file_service.register(test_db, 1, content=content, category="gear_image", ext=".jpg")
    second, reused = file_service.register(
        test_db, 1, content=content, category="gear_image", ext=".jpg"
    )
    assert reused is True
    assert second.id == first.id
    assert _physical_names(1, "gears") == [f"{_md5(content)}.jpg"]


# ==================== C3：同用户单记录 ====================


def test_register_same_md5_single_record(test_db):
    """同一用户同一 MD5 只保留一条 File 记录"""
    content = b"single-record"
    for _ in range(3):
        file_service.register(test_db, 1, content=content, category="video", ext=".mp4")
    test_db.commit()
    records = test_db.query(File).filter(File.user_id == 1, File.deleted_at.is_(None)).all()
    assert len(records) == 1
    assert records[0].md5 == _md5(content)


def test_register_different_users_have_own_record(test_db):
    """不同用户互不影响，各自持有自己的记录与物理文件"""
    content = b"shared-between-users"
    r1, _ = file_service.register(test_db, 1, content=content, category="gear_image", ext=".jpg")
    r2, _ = file_service.register(test_db, 2, content=content, category="gear_image", ext=".jpg")
    assert r1.id != r2.id
    assert r1.rel_path == f"gears/1/{_md5(content)}.jpg"
    assert r2.rel_path == f"gears/2/{_md5(content)}.jpg"


def test_register_after_soft_delete_reinserts(test_db):
    """软删后重新上传同一内容可以再次落库"""
    content = b"reinsert-after-delete"
    first, _ = file_service.register(test_db, 1, content=content, category="avatar", ext=".jpg")
    assert file_service.soft_delete(test_db, first.id) is True
    test_db.commit()

    second, reused = file_service.register(
        test_db, 1, content=content, category="avatar", ext=".jpg"
    )
    test_db.commit()
    assert second.id != first.id
    assert reused is False


def test_active_user_md5_partial_unique_index_exists(test_db):
    """部分唯一索引 (user_id, md5) WHERE deleted_at IS NULL 必须存在"""
    rows = test_db.execute(text_pragma_files_index_list()).fetchall()
    names = {row[1] for row in rows}
    assert "uq_files_user_md5_active" in names


def text_pragma_files_index_list():
    from sqlalchemy import text

    return text("PRAGMA index_list('files')")


# ==================== 引用计数初始值 ====================


def test_register_without_business_has_zero_ref_count(test_db):
    """未绑定业务的文件 ref_count = 0（等待业务绑定后 +1）"""
    record, _ = file_service.register(
        test_db, 1, content=b"no-business", category="video", ext=".mp4"
    )
    assert record.ref_count == 0


def test_register_with_business_binds_once(test_db):
    """登记时带 business 直接完成绑定，ref_count = 1"""
    record, _ = file_service.register(
        test_db,
        1,
        content=b"with-business",
        category="gear_image",
        ext=".jpg",
        business=("gear", 11),
    )
    assert record.ref_count == 1
    assert record.business_type == "gear"
    assert record.business_id == 11


# ==================== 批量登记 ====================


def test_register_batch_dedups_and_flushes(test_db):
    """批量登记去重：相同 MD5 只落一条，全部可用 id"""
    from app.services.file_service import FileDraft

    c1 = b"batch-1"
    c2 = b"batch-2"
    drafts = [
        FileDraft(src_path="", md5=_md5(c1), size=len(c1), upload_source="video_frame", ext=".jpg"),
        FileDraft(src_path="", md5=_md5(c2), size=len(c2), upload_source="video_frame", ext=".jpg"),
        FileDraft(src_path="", md5=_md5(c1), size=len(c1), upload_source="video_frame", ext=".jpg"),
    ]
    records = file_service.register_batch(test_db, 5, drafts)
    test_db.commit()
    assert len(records) == len(drafts)  # 与入参对齐，去重项复用同一记录
    assert all(r.id is not None for r in records)
    assert len({r.id for r in records}) == 2
    assert {r.md5 for r in records} == {_md5(c1), _md5(c2)}
    assert records[0].id == records[2].id
