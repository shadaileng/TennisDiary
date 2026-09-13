"""C5 文件扫描：基于业务引用注册表的五态分类

| 状态              | 含义                                       |
|-------------------|--------------------------------------------|
| in_use            | 已登记，且被业务记录引用                   |
| unreferenced      | 已登记，但无任何业务引用                   |
| missing           | 已登记，但物理文件缺失                     |
| orphan            | 磁盘有文件，但 File 表无记录（磁盘孤儿）   |
| unregistered_ref  | 业务记录引用了未登记的路径                 |
"""

import os

import pytest

from app.models.gear import Gear
from app.services import file_service

pytestmark = pytest.mark.fast


def _write_disk_file(rel_path: str, content: bytes = b"x") -> None:
    from app.core.config import settings

    abs_path = os.path.join(str(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)


def _status_of(report: dict, rel_path: str) -> str | None:
    for item in report["items"]:
        if item["rel_path"] == rel_path:
            return item["status"]
    return None


def _gear(test_db, user_id: int, photo: str) -> Gear:
    gear = Gear(user_id=user_id, name="球拍", photo=photo)
    test_db.add(gear)
    test_db.commit()
    return gear


# ==================== 五态判定 ====================


def test_scan_in_use_when_business_references(test_db):
    """业务记录引用的已登记文件 → in_use"""
    record, _ = file_service.register(
        test_db, 1, content=b"used", category="gear_image", ext=".jpg"
    )
    gear = _gear(test_db, 1, record.rel_path)
    file_service.bind(test_db, 1, record.rel_path, "gear", gear.id, "photo")

    report = file_service.scan(test_db)
    assert _status_of(report, record.rel_path) == "in_use"


def test_scan_unreferenced_when_no_business(test_db):
    """已登记但无业务引用 → unreferenced"""
    record, _ = file_service.register(
        test_db, 1, content=b"unused", category="gear_image", ext=".jpg"
    )

    report = file_service.scan(test_db)
    assert _status_of(report, record.rel_path) == "unreferenced"


def test_scan_missing_when_physical_file_gone(test_db):
    """已登记但物理文件缺失 → missing"""
    record, _ = file_service.register(
        test_db, 1, content=b"gone", category="gear_image", ext=".jpg"
    )
    os.unlink(file_service.abs_of(record.rel_path))

    report = file_service.scan(test_db)
    assert _status_of(report, record.rel_path) == "missing"


def test_scan_orphan_when_disk_file_unregistered(test_db):
    """磁盘有文件但未登记 → orphan"""
    _write_disk_file("videos/9/stray.mp4", b"stray")

    report = file_service.scan(test_db)
    assert _status_of(report, "videos/9/stray.mp4") == "orphan"


def test_scan_unregistered_ref_when_business_points_to_unknown(test_db):
    """业务记录引用了未登记的路径 → unregistered_ref"""
    _gear(test_db, 1, "gears/1/not-registered.jpg")

    report = file_service.scan(test_db)
    assert _status_of(report, "gears/1/not-registered.jpg") == "unregistered_ref"


def test_scan_reports_status_counts(test_db):
    """报告给出五态计数与扫描总量"""
    used, _ = file_service.register(
        test_db, 1, content=b"c-used", category="gear_image", ext=".jpg"
    )
    gear = _gear(test_db, 1, used.rel_path)
    file_service.bind(test_db, 1, used.rel_path, "gear", gear.id, "photo")
    free, _ = file_service.register(
        test_db, 1, content=b"c-free", category="gear_image", ext=".jpg"
    )
    _write_disk_file("videos/3/orphan.mp4")
    _gear(test_db, 2, "gears/2/unknown.jpg")

    report = file_service.scan(test_db)
    counts = report["status_counts"]
    assert counts["in_use"] == 1
    assert counts["unreferenced"] >= 1
    assert counts["orphan"] >= 1
    assert counts["unregistered_ref"] == 1
    assert report["registered_files"] >= 2
    assert _status_of(report, free.rel_path) == "unreferenced"


def test_scan_can_filter_by_user(test_db):
    """按用户过滤时只包含该用户的记录"""
    r1, _ = file_service.register(test_db, 1, content=b"u1", category="gear_image", ext=".jpg")
    r2, _ = file_service.register(test_db, 2, content=b"u2", category="gear_image", ext=".jpg")

    report = file_service.scan(test_db, user_id=2)
    paths = {item["rel_path"] for item in report["items"]}
    assert r2.rel_path in paths
    assert r1.rel_path not in paths


def test_scan_item_carries_business_refs(test_db):
    """扫描项带出引用它的业务记录，便于管理端反查归属"""
    record, _ = file_service.register(
        test_db, 1, content=b"ref-detail", category="gear_image", ext=".jpg"
    )
    gear = _gear(test_db, 1, record.rel_path)
    file_service.bind(test_db, 1, record.rel_path, "gear", gear.id, "photo")

    report = file_service.scan(test_db)
    item = next(i for i in report["items"] if i["rel_path"] == record.rel_path)
    assert item["status"] == "in_use"
    assert any(
        ref["business_type"] == "gear" and ref["business_id"] == gear.id
        for ref in item["business_refs"]
    )
