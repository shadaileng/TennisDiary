"""C4 引用计数：业务关联时自动加减

- 业务记录关联受管文件 → +1；解除关联 → -1
- rebind 按业务记录当前引用集合做差量，重复调用不重复计数
- 删除业务记录 → 关联文件全部 -1
- 归零文件不立即删除，由 cleanup_unbound 在宽限期后回收
"""

import time

import pytest

from app.models.gear import Gear
from app.models.user import User
from app.services import file_service

pytestmark = pytest.mark.fast


def _make_user(test_db, user_id: int = 1) -> User:
    user = User(id=user_id, openid=f"openid-{user_id}", nickname="u")
    test_db.add(user)
    test_db.commit()
    return user


def _make_gear(test_db, user_id: int = 1, photo: str = "") -> Gear:
    gear = Gear(user_id=user_id, name="球拍", photo=photo)
    test_db.add(gear)
    test_db.commit()
    return gear


# ==================== bind / unbind ====================


def test_bind_increments_ref_count(test_db):
    """同一文件被多条业务记录引用时逐一 +1"""
    record, _ = file_service.register(
        test_db, 1, content=b"gear-a", category="gear_image", ext=".jpg"
    )
    file_service.bind(test_db, 1, record.rel_path, "gear", 5)
    assert record.ref_count == 1
    assert record.business_type == "gear"
    assert record.business_id == 5

    file_service.bind(test_db, 1, record.rel_path, "gear", 6)
    assert record.ref_count == 2


def test_bind_missing_file_returns_none(test_db):
    """文件未登记时绑定失败并返回 None（不静默丢计数）"""
    assert file_service.bind(test_db, 1, "gears/1/nope.jpg", "gear", 5) is None


def test_unbind_decrements_floor_zero(test_db):
    """解绑递减且不低于 0"""
    record, _ = file_service.register(
        test_db, 1, content=b"gear-b", category="gear_image", ext=".jpg"
    )
    file_service.bind(test_db, 1, record.rel_path, "gear", 5)
    file_service.unbind(test_db, 1, record.rel_path, "gear", 5)
    assert record.ref_count == 0
    file_service.unbind(test_db, 1, record.rel_path, "gear", 5)
    assert record.ref_count == 0


def test_unbind_does_not_soft_delete_immediately(test_db):
    """归零不立即软删，交由宽限期回收"""
    record, _ = file_service.register(
        test_db, 1, content=b"gear-c", category="gear_image", ext=".jpg"
    )
    file_service.bind(test_db, 1, record.rel_path, "gear", 5)
    file_service.unbind(test_db, 1, record.rel_path, "gear", 5)
    assert record.deleted_at is None


# ==================== rebind（换图 / 更新） ====================


def test_rebind_replaces_old_reference(test_db):
    """换图：旧文件 -1，新文件 +1"""
    old, _ = file_service.register(
        test_db, 1, content=b"old-photo", category="gear_image", ext=".jpg"
    )
    new, _ = file_service.register(
        test_db, 1, content=b"new-photo", category="gear_image", ext=".jpg"
    )
    gear = _make_gear(test_db, photo=old.rel_path)
    file_service.bind(test_db, 1, old.rel_path, "gear", gear.id)
    assert old.ref_count == 1

    gear.photo = new.rel_path
    test_db.commit()
    file_service.rebind(test_db, 1, "gear", gear.id, [new.rel_path])

    assert old.ref_count == 0
    assert new.ref_count == 1


def test_rebind_is_idempotent(test_db):
    """重复 rebind 同一集合不重复计数"""
    record, _ = file_service.register(
        test_db, 1, content=b"stable", category="gear_image", ext=".jpg"
    )
    gear = _make_gear(test_db, photo=record.rel_path)

    for _ in range(3):
        file_service.rebind(test_db, 1, "gear", gear.id, [record.rel_path])

    assert record.ref_count == 1


def test_rebind_avatar_updates_user(test_db):
    """头像换图：旧头像 -1，新头像 +1"""
    _make_user(test_db, 1)
    old, _ = file_service.register(test_db, 1, content=b"avatar-old", category="avatar", ext=".jpg")
    new, _ = file_service.register(test_db, 1, content=b"avatar-new", category="avatar", ext=".jpg")

    user = test_db.query(User).filter(User.id == 1).first()
    user.avatar_url = old.rel_path
    test_db.commit()
    file_service.rebind(test_db, 1, "user", 1, [old.rel_path])
    assert old.ref_count == 1

    user.avatar_url = new.rel_path
    test_db.commit()
    file_service.rebind(test_db, 1, "user", 1, [new.rel_path])

    assert old.ref_count == 0
    assert new.ref_count == 1


# ==================== unbind_record（删除业务记录） ====================


def test_unbind_record_releases_all_files(test_db):
    """删除装备记录时，其引用的文件全部 -1"""
    photo, _ = file_service.register(
        test_db, 1, content=b"gear-photo", category="gear_image", ext=".jpg"
    )
    extra, _ = file_service.register(
        test_db, 1, content=b"gear-extra", category="gear_image", ext=".jpg"
    )
    gear = _make_gear(test_db, photo=photo.rel_path)
    file_service.bind(test_db, 1, photo.rel_path, "gear", gear.id)
    file_service.bind(test_db, 1, extra.rel_path, "gear", gear.id)
    assert (photo.ref_count, extra.ref_count) == (1, 1)

    released = file_service.unbind_record(test_db, "gear", gear.id)
    assert released == 2
    assert (photo.ref_count, extra.ref_count) == (0, 0)


# ==================== cleanup_unbound（宽限期回收） ====================


def test_cleanup_unbound_recycles_after_grace(test_db):
    """超过宽限期且未被任何业务引用的文件被软删"""
    record, _ = file_service.register(
        test_db, 1, content=b"abandoned", category="gear_image", ext=".jpg"
    )
    record.created_at = time.time() - 48 * 3600
    test_db.commit()

    assert file_service.cleanup_unbound(test_db, grace_hours=24) == 1
    assert record.deleted_at is not None


def test_cleanup_unbound_keeps_fresh_and_bound(test_db):
    """宽限期内 / 已被业务引用的文件不被回收"""
    fresh, _ = file_service.register(
        test_db, 1, content=b"fresh", category="gear_image", ext=".jpg"
    )
    bound, _ = file_service.register(
        test_db, 1, content=b"bound", category="gear_image", ext=".jpg"
    )
    bound.created_at = time.time() - 48 * 3600
    gear = _make_gear(test_db, photo=bound.rel_path)
    file_service.bind(test_db, 1, bound.rel_path, "gear", gear.id)
    test_db.commit()

    assert file_service.cleanup_unbound(test_db, grace_hours=24) == 0
    assert fresh.deleted_at is None
    assert bound.deleted_at is None
