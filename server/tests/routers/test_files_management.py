"""文件管理测试（138：统一门面 + MD5 命名 + 引用计数）

覆盖：
- 基础操作（登记后 File 记录创建、归属校验、路径穿越防护）
- MD5 秒传（同一用户同内容复用同一记录与物理文件）
- 路径工具（build_rel_path / resolve / abs_of ↔ rel_of）
- 上传端点（头像 / 装备图登记）
- 业务删除联动（gear 删除、avatar 更新 → 旧文件 -1）
- 分析文件解绑（video_url / thumb / 骨架产物）
- 并发竞态（同 MD5 不同用户互不影响）

说明：旧实现内部的 `get_or_create_file` / 路径工具 / `decrement_*` 均已收口到
`file_service` 门面，测试改为面向门面 API，避免与内部实现耦合。
"""

import hashlib
import json
import os
import time
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.models.analysis import Analysis
from app.models.file import File
from app.models.gear import Gear
from app.models.user import User
from app.services import file_service

# ==================== 辅助 ====================


def _write_upload_file(rel_path: str, content: bytes = b"hello-world") -> str:
    """在 UPLOAD_DIR 下写入一个上传文件，返回相对路径"""
    file_service.write_bytes(file_service.abs_of(rel_path), content)
    return rel_path


_seq = 0


def _next_uid():
    """生成唯一 user_id，避免跨测试唯一约束冲突"""
    global _seq
    _seq += 1
    return 3000 + _seq


def _create_file_record(
    test_db,
    user_id: int,
    rel_path: str,
    md5: str | None = None,
    ref_count: int = 0,
    upload_source: str = "gear_image",
    size_bytes: int = 11,
    business_type: str | None = None,
    business_id: int | None = None,
):
    """创建文件记录（含物理文件）；ref_count 默认 0，绑定后由门面 +1"""
    if md5 is None:
        md5 = hashlib.md5(b"hello-world").hexdigest()
    record = File(
        user_id=user_id,
        md5=md5,
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=size_bytes,
        mime_type="image/jpeg",
        upload_source=upload_source,
        ref_count=ref_count,
        business_type=business_type,
        business_id=business_id,
        created_at=time.time(),
    )
    test_db.add(record)
    test_db.commit()
    _write_upload_file(rel_path)
    return record


@pytest.fixture(autouse=True)
def _mock_check():
    """自动跳过微信内容安全检查（测试环境无真实 API）"""
    with patch("app.services.content_security.check_image_sync") as mock:
        mock.return_value = None
        yield mock


# ==================== 基础操作 ====================


class TestFileBasicOps:
    """登记后自动创建 File 记录，下载可读取"""

    def test_file_record_created(self, test_db):
        record, reused = file_service.register(
            db=test_db, user_id=1, content=b"basic", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        assert reused is False
        assert record.id is not None
        assert record.rel_path == f"gears/1/{hashlib.md5(b'basic').hexdigest()}.jpg"

    def test_file_ownership_check(self, test_db):
        uid = _next_uid()
        rel = f"gears/{uid}/own.jpg"
        _create_file_record(test_db, uid, rel, md5=hashlib.md5(rel.encode()).hexdigest())
        assert file_service.owned_by(test_db, uid, rel) is True
        assert file_service.owned_by(test_db, uid + 1, rel) is False

    def test_file_other_user_blocked(self, auth_client, test_db):
        """下载他人文件返回 404"""
        uid = _next_uid()
        rel = f"gears/{uid}/blocked.jpg"
        _create_file_record(test_db, uid, rel, md5=hashlib.md5(rel.encode()).hexdigest())
        resp = auth_client.get(f"/api/files/{rel}")
        assert resp.status_code == 404

    def test_file_nonexistent_returns_404(self, auth_client):
        resp = auth_client.get("/api/files/gears/999999/not-exist.jpg")
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, auth_client):
        resp = auth_client.get("/api/files/../../../etc/passwd")
        assert resp.status_code in (404, 422)


# ==================== MD5 秒传 ====================


class TestMD5AndInstantUpload:
    def test_instant_upload_reuses_path(self, test_db):
        """同一用户重复上传同一内容：复用同一记录与物理路径"""
        uid = _next_uid()
        first, _ = file_service.register(
            db=test_db, user_id=uid, content=b"instant", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        second, reused = file_service.register(
            db=test_db, user_id=uid, content=b"instant", category="gear_image", ext=".jpg"
        )
        test_db.commit()

        assert reused is True
        assert first.id == second.id
        assert first.rel_path == second.rel_path
        assert test_db.query(File).filter(File.user_id == uid).count() == 1

    def test_different_md5_independent(self, test_db):
        """不同内容各自独立建记录"""
        uid = _next_uid()
        a, _ = file_service.register(
            db=test_db, user_id=uid, content=b"content-a", category="gear_image", ext=".jpg"
        )
        b, _ = file_service.register(
            db=test_db, user_id=uid, content=b"content-b", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        assert a.id != b.id
        assert a.rel_path != b.rel_path

    def test_ref_count_increments_on_bind(self, test_db):
        """业务绑定一次 +1"""
        uid = _next_uid()
        record, _ = file_service.register(
            db=test_db, user_id=uid, content=b"bind-count", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        file_service.bind(test_db, uid, record.rel_path, "gear", 1)
        file_service.bind(test_db, uid, record.rel_path, "gear", 2)
        assert record.ref_count == 2

    def test_ref_count_zero_not_deleted(self, test_db):
        """解绑归零后不立即软删（交由宽限期回收）"""
        uid = _next_uid()
        record, _ = file_service.register(
            db=test_db, user_id=uid, content=b"zero", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        file_service.bind(test_db, uid, record.rel_path, "gear", 1)
        file_service.unbind(test_db, uid, record.rel_path, "gear", 1)
        assert record.ref_count == 0
        assert record.deleted_at is None


# ==================== 路径工具 ====================


class TestPathTools:
    def test_build_rel_path_format(self):
        md5 = "a" * 32
        assert file_service.build_rel_path(1, md5, ".jpg", "avatar") == f"avatars/1/{md5}.jpg"
        assert file_service.build_rel_path(2, md5, "png", "gear_image") == f"gears/2/{md5}.png"

    def test_resolve_within_upload_dir(self):
        upload_dir = os.path.abspath(settings.UPLOAD_DIR)
        assert file_service.resolve("videos/1/a.mp4") == os.path.join(
            upload_dir, "videos", "1", "a.mp4"
        )

    def test_resolve_traversal_returns_none(self):
        assert file_service.resolve("../../../etc/passwd") is None

    def test_abs_rel_roundtrip(self):
        rel = "videos/7/x.mp4"
        assert file_service.rel_of(file_service.abs_of(rel)) == rel


# ==================== 上传端点 ====================


class TestUploadFileRecord:
    def test_upload_avatar_creates_file_record(self, auth_client, test_db):
        uid = 1  # conftest 的 mock 用户 ID
        resp = auth_client.post(
            "/api/upload/avatar",
            files={"file": ("avatar.jpg", b"avatar-bytes", "image/jpeg")},
        )
        assert resp.status_code == 200
        url = resp.json()["data"]["url"]
        assert url.startswith(f"avatars/{uid}/")
        assert url.endswith(f"{hashlib.md5(b'avatar-bytes').hexdigest()}.jpg")

    def test_upload_gear_image_creates_file_record(self, auth_client, test_db):
        uid = 1  # conftest 的 mock 用户 ID
        resp = auth_client.post(
            "/api/upload/gear-image",
            files={"file": ("gear.png", b"gear-bytes", "image/png")},
        )
        assert resp.status_code == 200
        url = resp.json()["data"]["url"]
        assert url.startswith(f"gears/{uid}/")
        assert url.endswith(f"{hashlib.md5(b'gear-bytes').hexdigest()}.png")


# ==================== 业务删除联动 ====================


class TestBusinessDeleteLinkage:
    def test_delete_gear_releases_photo(self, auth_client, test_db):
        uid = 1  # conftest 的 mock 用户 ID
        photo = f"gears/{uid}/gear-photo.jpg"
        _create_file_record(test_db, uid, photo, md5=hashlib.md5(photo.encode()).hexdigest())

        gear = Gear(user_id=uid, name="球拍", photo=photo)
        test_db.add(gear)
        test_db.commit()
        file_service.bind(test_db, uid, photo, "gear", gear.id, "photo")
        test_db.commit()

        record = test_db.query(File).filter(File.rel_path == photo).first()
        assert record.ref_count == 1

        resp = auth_client.delete(f"/api/gears/{gear.id}")
        assert resp.status_code == 200

        test_db.refresh(record)
        assert record.ref_count == 0

    def test_update_avatar_releases_old_file(self, test_db):
        """头像换图：旧头像 -1，新头像 +1（经 rebind）"""
        uid = _next_uid()
        old = f"avatars/{uid}/old.jpg"
        new = f"avatars/{uid}/new.jpg"
        _create_file_record(test_db, uid, old, md5=hashlib.md5(old.encode()).hexdigest())
        _create_file_record(test_db, uid, new, md5=hashlib.md5(new.encode()).hexdigest())

        user = User(id=uid, openid=f"openid-{uid}", avatar_url=old)
        test_db.add(user)
        test_db.commit()
        file_service.rebind(test_db, uid, "user", uid, [old], field="avatar_url")
        test_db.commit()

        user.avatar_url = new
        test_db.commit()
        file_service.rebind(test_db, uid, "user", uid, [new], field="avatar_url")

        old_rec = test_db.query(File).filter(File.rel_path == old).first()
        new_rec = test_db.query(File).filter(File.rel_path == new).first()
        assert old_rec.ref_count == 0
        assert new_rec.ref_count == 1


# ==================== 分析文件解绑 ====================


class TestAnalysisFiles:
    def test_unbind_record_releases_video_and_thumb(self, test_db):
        uid = _next_uid()
        video = f"videos/{uid}/a.mp4"
        thumb = f"videos/{uid}/a.jpg"
        _create_file_record(
            test_db, uid, video, md5=hashlib.md5(video.encode()).hexdigest(), upload_source="video"
        )
        _create_file_record(
            test_db,
            uid,
            thumb,
            md5=hashlib.md5(thumb.encode()).hexdigest(),
            upload_source="analysis_thumb",
        )
        analysis = Analysis(user_id=uid, date="2026-01-01", video_url=video, thumb=thumb)
        test_db.add(analysis)
        test_db.commit()
        for path in (video, thumb):
            file_service.bind(test_db, uid, path, "analysis", analysis.id)
        test_db.commit()

        released = file_service.unbind_record(test_db, "analysis", analysis.id)
        assert released == 2
        assert test_db.query(File).filter(File.rel_path == video).first().ref_count == 0

    def test_unbind_record_releases_skeleton_from_pose(self, test_db):
        uid = _next_uid()
        sk = f"videos/{uid}/a_skeleton.mp4"
        _create_file_record(
            test_db,
            uid,
            sk,
            md5=hashlib.md5(sk.encode()).hexdigest(),
            upload_source="skeleton_video",
        )
        analysis = Analysis(
            user_id=uid,
            date="2026-01-01",
            pose=json.dumps({"skeleton_video_url": sk, "skeleton_frames": []}),
        )
        test_db.add(analysis)
        test_db.commit()
        file_service.bind(test_db, uid, sk, "analysis", analysis.id)
        test_db.commit()

        file_service.unbind_record(test_db, "analysis", analysis.id)
        assert test_db.query(File).filter(File.rel_path == sk).first().ref_count == 0

    def test_empty_pose_no_effect(self, test_db):
        uid = _next_uid()
        analysis = Analysis(user_id=uid, date="2026-01-01", pose=None)
        test_db.add(analysis)
        test_db.commit()
        assert file_service.unbind_record(test_db, "analysis", analysis.id) == 0


# ==================== 并发竞态 ====================


class TestConcurrency:
    def test_same_md5_different_users_independent(self, test_db):
        r1, _ = file_service.register(
            db=test_db, user_id=_next_uid(), content=b"shared", category="gear_image", ext=".jpg"
        )
        r2, _ = file_service.register(
            db=test_db, user_id=_next_uid(), content=b"shared", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        assert r1.id != r2.id
        assert r1.rel_path != r2.rel_path

    def test_ref_count_isolation(self, test_db):
        u1, u2 = _next_uid(), _next_uid()
        r1, _ = file_service.register(
            db=test_db, user_id=u1, content=b"iso", category="gear_image", ext=".jpg"
        )
        r2, _ = file_service.register(
            db=test_db, user_id=u2, content=b"iso", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        file_service.bind(test_db, u1, r1.rel_path, "gear", 1)
        assert r2.ref_count == 0

    def test_delete_does_not_break_other_users(self, test_db):
        u1, u2 = _next_uid(), _next_uid()
        r1, _ = file_service.register(
            db=test_db, user_id=u1, content=b"del-iso", category="gear_image", ext=".jpg"
        )
        r2, _ = file_service.register(
            db=test_db, user_id=u2, content=b"del-iso", category="gear_image", ext=".jpg"
        )
        test_db.commit()
        file_service.soft_delete(test_db, r1.id)
        test_db.commit()
        assert file_service.exists(r1.rel_path) is False
        assert file_service.exists(r2.rel_path) is True


def test_check_endpoint_hit(auth_client, test_db):
    """秒传预检：已登记文件按 MD5 命中"""
    uid = 1  # conftest 的 mock 用户 ID
    content = b"check-hit-content"
    file_service.register(
        db=test_db,
        user_id=uid,
        content=content,
        category="gear_image",
        ext=".jpg",
        security_checked=True,
    )
    test_db.commit()
    resp = auth_client.post(
        "/api/upload/check",
        json={"md5": hashlib.md5(content).hexdigest(), "size_bytes": len(content)},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["hit"] is True
    assert data["url"] is not None


def test_pending_upload_recycled_after_grace(test_db):
    """上传后未绑定业务的文件在宽限期后被回收"""
    uid = _next_uid()
    record, _ = file_service.register(
        db=test_db, user_id=uid, content=b"abandoned-upload", category="gear_image", ext=".jpg"
    )
    record.created_at = time.time() - 48 * 3600
    test_db.commit()

    assert file_service.cleanup_unbound(test_db, grace_hours=24) == 1
    assert record.deleted_at is not None
