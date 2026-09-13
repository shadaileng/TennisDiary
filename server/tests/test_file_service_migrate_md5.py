"""C6 存量迁移：uuid 命名 → {md5}.{后缀} + 业务表 URL 回填

- 支持 dry_run 预演（不落任何改动）
- 重命名物理文件并同步 File 记录 rel_path
- 回填业务表（users.avatar_url / gears.photo / analyses.*）中的旧路径
- 幂等：重复执行无副作用
"""

import hashlib
import os

import pytest

from app.core.config import settings
from app.models.file import File
from app.models.gear import Gear
from app.services import file_service

pytestmark = pytest.mark.fast


def _legacy_file(test_db, user_id: int, rel_path: str, content: bytes, upload_source: str) -> File:
    """模拟存量记录：uuid 命名 + 物理文件已存在"""
    abs_path = os.path.join(str(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)

    record = File(
        user_id=user_id,
        md5=hashlib.md5(content).hexdigest(),
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=len(content),
        mime_type="",
        upload_source=upload_source,
        ref_count=1,
        created_at=0,
    )
    test_db.add(record)
    test_db.commit()
    return record


# ==================== dry_run 预演 ====================


def test_dry_run_reports_without_changes(test_db):
    """预演只出报告，不改名、不改库"""
    record = _legacy_file(test_db, 1, "gears/1/uuid-aaaa.jpg", b"legacy-a", "gear_image")

    report = file_service.migrate_to_md5(test_db, dry_run=True)
    test_db.rollback()

    assert report["dry_run"] is True
    assert report["renamed"] >= 1
    assert record.rel_path == "gears/1/uuid-aaaa.jpg"
    assert os.path.isfile(os.path.join(str(settings.UPLOAD_DIR), "gears/1/uuid-aaaa.jpg"))


# ==================== 正式迁移 ====================


def test_migrate_renames_physical_file_to_md5(test_db):
    """物理文件重命名为 {md5}.{后缀}，记录同步更新"""
    content = b"legacy-b"
    record = _legacy_file(test_db, 1, "gears/1/uuid-bbbb.jpg", content, "gear_image")
    md5 = hashlib.md5(content).hexdigest()

    file_service.migrate_to_md5(test_db, dry_run=False)
    test_db.commit()

    assert record.rel_path == f"gears/1/{md5}.jpg"
    assert file_service.exists(record.rel_path)
    assert not os.path.isfile(os.path.join(str(settings.UPLOAD_DIR), "gears/1/uuid-bbbb.jpg"))


def test_migrate_backfills_business_urls(test_db):
    """业务表中的旧路径被回填为新路径"""
    content = b"legacy-c"
    record = _legacy_file(test_db, 1, "gears/1/uuid-cccc.jpg", content, "gear_image")
    gear = Gear(user_id=1, name="球拍", photo=record.rel_path)
    test_db.add(gear)
    test_db.commit()

    file_service.migrate_to_md5(test_db, dry_run=False)
    test_db.commit()

    test_db.refresh(gear)
    assert gear.photo == record.rel_path


def test_migrate_is_idempotent(test_db):
    """重复执行不产生额外改动"""
    content = b"legacy-d"
    record = _legacy_file(test_db, 2, "avatars/2/uuid-dddd.png", content, "avatar")

    file_service.migrate_to_md5(test_db, dry_run=False)
    test_db.commit()
    first_path = record.rel_path

    report = file_service.migrate_to_md5(test_db, dry_run=False)
    test_db.commit()

    assert report["renamed"] == 0
    assert report["already_named"] >= 1
    assert record.rel_path == first_path


def test_migrate_reports_missing_physical_file(test_db):
    """物理文件已丢失的存量记录被单独报告，不阻断迁移"""
    record = File(
        user_id=3,
        md5="e" * 32,
        original_name="gone.jpg",
        rel_path="gears/3/uuid-eeee.jpg",
        size_bytes=10,
        upload_source="gear_image",
        ref_count=1,
        created_at=0,
    )
    test_db.add(record)
    test_db.commit()

    report = file_service.migrate_to_md5(test_db, dry_run=False)
    assert record.rel_path in report["missing_files"]
