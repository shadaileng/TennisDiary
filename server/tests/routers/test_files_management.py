"""文件管理路由测试（5.1-5.3, 5.5-5.7）

覆盖：
- 5.1 File 基础操作（上传后 File 记录创建、归属校验）
- 5.2 MD5 + 秒传（get_or_create_file、引用计数）
- 5.3 路径工具（resolve_safe_path、build_upload_dir、make_rel_path、abs_path_to_rel）
- 5.5 AI 分析（decrement_analysis_files、register_ai_files）
- 5.6 骨架文件注册（analysis.pose 骨架递减）
- 5.7 并发竞态（同 MD5 不同用户同时上传）
"""

import hashlib
import os
import time

from app.core.config import settings
from app.models.file import File

# ==================== 辅助 ====================


def _write_upload_file(rel_path: str, content: bytes = b"hello-world") -> str:
    """在 UPLOAD_DIR 下写入一个上传文件，返回相对路径"""
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
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
    ref_count: int = 1,
    upload_source: str = "gear_image",
    size_bytes: int = 11,
    business_type: str | None = None,
    business_id: int | None = None,
):
    """创建文件记录"""
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
    return record


# ==================== 5.1 File 基础操作 ====================


class TestFileBasicOps:
    """5.1 上传后自动创建 File 记录，下载可读取"""

    def test_file_record_created_on_upload(self, test_db):
        """上传后 File 记录自动创建"""
        uid = _next_uid()
        rel = _write_upload_file(f"avatars/{uid}/test.jpg")
        record = _create_file_record(test_db, user_id=uid, rel_path=rel)
        assert record.id is not None
        assert record.ref_count == 1
        assert record.md5 == hashlib.md5(b"hello-world").hexdigest()

    def test_file_ownership_check(self, auth_client, test_db):
        """自有 File 记录引用的文件可下载（mock_user.id=1）"""
        content = b"own-content-for-download"
        md5 = hashlib.md5(content).hexdigest()
        rel = _write_upload_file("avatars/1/own-download.jpg", content)
        _create_file_record(test_db, user_id=1, rel_path=rel, md5=md5)
        resp = auth_client.get(f"/api/files/{rel}")
        assert resp.status_code == 200
        assert resp.content == content

    def test_file_other_user_blocked(self, auth_client, test_db):
        """他人文件返回 404"""
        content = b"other-user-content"
        md5 = hashlib.md5(content).hexdigest()
        rel = _write_upload_file("avatars/999/other-blocked.jpg", content)
        _create_file_record(test_db, user_id=999, rel_path=rel, md5=md5)
        resp = auth_client.get(f"/api/files/{rel}")
        assert resp.status_code == 404

    def test_file_nonexistent_returns_404(self, auth_client):
        """不存在文件返回 404"""
        resp = auth_client.get("/api/files/images/missing.jpg")
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, auth_client):
        """路径穿越应被拒绝"""
        resp = auth_client.get("/api/files/../config.py")
        assert resp.status_code == 404
        resp2 = auth_client.get("/api/files/images/../../app/main.py")
        assert resp2.status_code == 404


# ==================== 5.2 MD5 + 秒传 ====================


class TestMD5AndInstantUpload:
    """5.2 相同 MD5 应秒传（复用物理文件路径），引用计数递增"""

    def test_instant_upload_reuses_path(self, test_db):
        """相同 MD5 同用户：秒传时创建新记录，复用物理路径，原记录 ref_count 递增"""
        from app.services.file_service import get_or_create_file

        uid = _next_uid()
        content = f"instant-{uid}".encode()
        rel = _write_upload_file(f"gears/{uid}/test.jpg", content)
        md5 = hashlib.md5(content).hexdigest()

        file_a, is_mirage = get_or_create_file(
            test_db,
            user_id=uid,
            md5=md5,
            rel_path=rel,
            upload_source="gear_image",
            original_name="test.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()
        assert not is_mirage
        assert file_a.rel_path == rel
        assert file_a.ref_count == 1

        # 同用户同 MD5：创建新记录（独立记录），复用物理路径，原记录 ref_count 递增
        file_b, is_mirage = get_or_create_file(
            test_db,
            user_id=uid,
            md5=md5,
            rel_path=f"gears/{uid}/duplicate.jpg",
            upload_source="gear_image",
            original_name="duplicate.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()
        assert is_mirage
        assert file_b.id != file_a.id  # 新记录，独立 ID
        assert file_b.rel_path == file_a.rel_path  # 复用物理路径
        test_db.refresh(file_a)
        assert file_a.ref_count == 2  # 原记录 ref_count 递增

    def test_different_md5_independent(self, test_db):
        """不同 MD5 独立记录"""
        from app.services.file_service import get_or_create_file

        uid = _next_uid()
        content_a = f"md5a-{uid}".encode()
        content_b = f"md5b-{uid}".encode()
        rel1 = _write_upload_file(f"gears/{uid}/a.jpg", content_a)
        rel2 = _write_upload_file(f"gears/{uid}/b.jpg", content_b)
        md5_a = hashlib.md5(content_a).hexdigest()
        md5_b = hashlib.md5(content_b).hexdigest()

        file_a, _ = get_or_create_file(
            test_db,
            user_id=uid,
            md5=md5_a,
            rel_path=rel1,
            upload_source="gear_image",
            original_name="a.jpg",
            size_bytes=len(content_a),
            mime_type="image/jpeg",
        )
        file_b, _ = get_or_create_file(
            test_db,
            user_id=uid,
            md5=md5_b,
            rel_path=rel2,
            upload_source="gear_image",
            original_name="b.jpg",
            size_bytes=len(content_b),
            mime_type="image/jpeg",
        )
        test_db.commit()
        assert file_a.rel_path != file_b.rel_path
        assert file_a.ref_count == 1
        assert file_b.ref_count == 1

    def test_ref_count_increments_on_instant(self, test_db):
        """秒传时 ref_count 递增"""
        from app.services.file_service import get_or_create_file

        uid = _next_uid()
        content = f"refcount-{uid}".encode()
        rel = _write_upload_file(f"gears/{uid}/original.jpg", content)
        md5 = hashlib.md5(content).hexdigest()

        first, _ = get_or_create_file(
            test_db,
            user_id=uid,
            md5=md5,
            rel_path=rel,
            upload_source="gear_image",
            original_name="original.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()  # flush (autoflush=False)
        assert first.ref_count == 1

        get_or_create_file(
            test_db,
            user_id=uid,
            md5=md5,
            rel_path=f"gears/{uid}/other.jpg",
            upload_source="gear_image",
            original_name="other.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()
        test_db.refresh(first)
        assert first.ref_count == 2

    def test_ref_count_zero_marks_deleted(self, test_db):
        """引用归零后 File 标记软删"""
        from app.services.file_service import decrement_ref_count

        uid = _next_uid()
        content = f"refdel-{uid}".encode()
        rel = _write_upload_file(f"gears/{uid}/ref-test.jpg", content)
        md5 = hashlib.md5(content).hexdigest()
        record = _create_file_record(test_db, user_id=uid, rel_path=rel, md5=md5, ref_count=1)

        decremented = decrement_ref_count(test_db, user_id=uid, rel_path=rel)
        assert decremented == 1
        test_db.commit()
        test_db.refresh(record)
        assert record.deleted_at is not None


# ==================== 5.3 路径工具 ====================


class TestPathTools:
    """5.3 resolve_safe_path / build_upload_dir / make_rel_path / abs_path_to_rel"""

    def test_resolve_safe_path_within_upload_dir(self):
        """合法相对路径解析到 UPLOAD_DIR 内"""
        from app.services.file_service import resolve_safe_path

        result = resolve_safe_path("avatars/1/test.jpg")
        assert result is not None
        assert os.path.isabs(result)
        assert os.path.abspath(settings.UPLOAD_DIR) in result

    def test_resolve_safe_path_traversal_returns_none(self):
        """路径穿越返回 None"""
        from app.services.file_service import resolve_safe_path

        assert resolve_safe_path("../config.py") is None
        assert resolve_safe_path("avatars/../../app/main.py") is None

    def test_build_upload_dir_creates_directory(self):
        """build_upload_dir 创建目录并返回绝对路径"""
        from app.services.file_service import build_upload_dir

        result = build_upload_dir("avatars", 42)
        assert os.path.isdir(result)
        assert os.path.isabs(result)
        assert "42" in result

    def test_make_rel_path_format(self):
        """make_rel_path 生成正斜杠格式"""
        from app.services.file_service import make_rel_path

        result = make_rel_path("avatars", 7, "abc.jpg")
        assert result == "avatars/7/abc.jpg"
        assert "\\" not in result

    def test_abs_path_to_rel_roundtrip(self):
        """abs_path_to_rel 与 rel_path_to_abs 可逆"""
        from app.services.file_service import abs_path_to_rel, rel_path_to_abs

        rel = "avatars/1/test.jpg"
        abs_p = rel_path_to_abs(rel)
        result = abs_path_to_rel(abs_p)
        assert result == rel


# ==================== 5.5 AI 分析 ====================


class TestAIAnalysisFiles:
    """5.5 decrement_analysis_files 递减 analysis 关联的所有文件引用计数"""

    def _make_analysis(self, user_id, **overrides):
        """创建一个假 Analysis 对象"""
        data = dict(
            id=1,
            user_id=user_id,
            date="2026-08-15",
            kind="综合",
            mode="full",
            score=72,
            summary="测试",
            thumb="analyses/thumb.jpg",
            highlights='["analyses/h1.jpg"]',
            video_url="analyses/video.mp4",
            pose=None,
            created_at=0,
        )
        data.update(overrides)
        return type("FakeAnalysis", (), data)()

    def test_decrement_main_files(self, test_db):
        """递减 thumb、video_url 的引用计数"""
        from app.services.file_service import decrement_analysis_files

        uid = _next_uid()
        _create_file_record(
            test_db,
            uid,
            "analyses/thumb.jpg",
            md5=hashlib.md5(b"thumb").hexdigest(),
            upload_source="video_frame",
        )
        _create_file_record(
            test_db,
            uid,
            "analyses/video.mp4",
            md5=hashlib.md5(b"video").hexdigest(),
            upload_source="video",
        )
        analysis = self._make_analysis(uid)

        count = decrement_analysis_files(test_db, analysis)
        assert count == 2

    def test_decrement_highlights(self, test_db):
        """递减 highlights 中的文件引用计数"""
        from app.services.file_service import decrement_analysis_files

        uid = _next_uid()
        _create_file_record(
            test_db,
            uid,
            "analyses/h1.jpg",
            md5=hashlib.md5(b"high1").hexdigest(),
            upload_source="video_frame",
        )
        analysis = self._make_analysis(uid, thumb=None, video_url=None)

        count = decrement_analysis_files(test_db, analysis)
        assert count == 1

    def test_decrement_skeleton_frames(self, test_db):
        """递减 pose.skeleton_frames 引用计数"""
        import json

        from app.services.file_service import decrement_analysis_files

        uid = _next_uid()
        _create_file_record(
            test_db,
            uid,
            "analyses/sk1.jpg",
            md5=hashlib.md5(b"sk1").hexdigest(),
            upload_source="skeleton",
        )
        _create_file_record(
            test_db,
            uid,
            "analyses/sk2.jpg",
            md5=hashlib.md5(b"sk2").hexdigest(),
            upload_source="skeleton",
        )
        pose_data = {"skeleton_frames": ["analyses/sk1.jpg", "analyses/sk2.jpg"]}
        analysis = self._make_analysis(
            uid, thumb=None, highlights=None, video_url=None, pose=json.dumps(pose_data)
        )

        count = decrement_analysis_files(test_db, analysis)
        assert count == 2

    def test_register_ai_files_creates_records(self, test_db):
        """register_ai_files 为骨架文件创建 File 记录"""
        from app.services.file_service import register_ai_files

        uid = _next_uid()
        abs_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), f"analyses/{uid}")
        os.makedirs(abs_dir, exist_ok=True)
        for name in ["sk_a.jpg", "sk_b.jpg"]:
            with open(os.path.join(abs_dir, name), "wb") as f:
                f.write(b"skeleton-data")

        records = register_ai_files(
            test_db,
            user_id=uid,
            paths=[f"analyses/{uid}/sk_a.jpg", f"analyses/{uid}/sk_b.jpg"],
            business_type="analysis",
            business_id=10,
        )
        assert len(records) == 2
        assert all(r.upload_source == "skeleton" for r in records)
        assert all(r.business_type == "analysis" for r in records)


# ==================== 5.6 骨架文件注册 ====================


class TestSkeletonRegistration:
    """5.6 骨架帧注册后关联到 Analysis"""

    def test_skeleton_files_linked_to_analysis(self, test_db):
        """register_ai_files 创建的记录可被 decrement_analysis_files 递减"""
        import json

        from app.services.file_service import decrement_analysis_files, register_ai_files

        uid = _next_uid()
        abs_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), f"skeletons/{uid}")
        os.makedirs(abs_dir, exist_ok=True)
        paths = [f"skeletons/{uid}/frame1.jpg", f"skeletons/{uid}/frame2.jpg"]
        for i, name in enumerate(["frame1.jpg", "frame2.jpg"]):
            with open(os.path.join(abs_dir, name), "wb") as f:
                f.write(f"skel-data-{i}".encode())

        register_ai_files(
            test_db,
            user_id=uid,
            paths=paths,
            business_type="analysis",
            business_id=5,
        )
        test_db.commit()

        pose_data = {"skeleton_frames": paths}
        analysis = type(
            "FakeAnalysis",
            (),
            {
                "user_id": uid,
                "thumb": None,
                "video_url": None,
                "highlights": None,
                "pose": json.dumps(pose_data),
            },
        )()

        count = decrement_analysis_files(test_db, analysis)
        assert count == 2

    def test_skeleton_video_url_decremented(self, test_db):
        """skeleton_video_url 也被递减"""
        import json

        from app.services.file_service import decrement_analysis_files

        uid = _next_uid()
        _create_file_record(
            test_db,
            uid,
            f"skeletons/{uid}/video.mp4",
            md5=hashlib.md5(b"skvid").hexdigest(),
            upload_source="skeleton",
        )
        pose_data = {"skeleton_video_url": f"skeletons/{uid}/video.mp4"}
        analysis = type(
            "FakeAnalysis",
            (),
            {
                "user_id": uid,
                "thumb": None,
                "video_url": None,
                "highlights": None,
                "pose": json.dumps(pose_data),
            },
        )()

        count = decrement_analysis_files(test_db, analysis)
        assert count == 1

    def test_skeleton_thumb_decremented(self, test_db):
        """skeleton_thumb 也被递减"""
        import json

        from app.services.file_service import decrement_analysis_files

        uid = _next_uid()
        _create_file_record(
            test_db,
            uid,
            f"skeletons/{uid}/thumb.jpg",
            md5=hashlib.md5(b"skth").hexdigest(),
            upload_source="skeleton",
        )
        pose_data = {"skeleton_thumb": f"skeletons/{uid}/thumb.jpg"}
        analysis = type(
            "FakeAnalysis",
            (),
            {
                "user_id": uid,
                "thumb": None,
                "video_url": None,
                "highlights": None,
                "pose": json.dumps(pose_data),
            },
        )()

        count = decrement_analysis_files(test_db, analysis)
        assert count == 1

    def test_empty_pose_no_effect(self, test_db):
        """pose 为 None 时不影响"""
        from app.services.file_service import decrement_analysis_files

        uid = _next_uid()
        analysis = type(
            "FakeAnalysis",
            (),
            {
                "user_id": uid,
                "thumb": None,
                "video_url": None,
                "highlights": None,
                "pose": None,
            },
        )()

        count = decrement_analysis_files(test_db, analysis)
        assert count == 0


# ==================== 5.7 并发竞态 ====================


class TestConcurrency:
    """5.7 同 MD5 不同用户同时上传场景"""

    def test_same_md5_different_users_independent(self, test_db):
        """不同用户相同 MD5 各自独立，不交叉"""
        from app.services.file_service import get_or_create_file

        content = b"hello-world"
        md5 = hashlib.md5(content).hexdigest()
        uid1 = _next_uid()
        uid2 = _next_uid()
        rel1 = _write_upload_file(f"gears/{uid1}/concurrent1.jpg", content)
        rel2 = _write_upload_file(f"gears/{uid2}/concurrent2.jpg", content)

        r1, _ = get_or_create_file(
            test_db,
            user_id=uid1,
            md5=md5,
            rel_path=rel1,
            upload_source="gear_image",
            original_name="concurrent1.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()  # flush (autoflush=False)
        r2, _ = get_or_create_file(
            test_db,
            user_id=uid2,
            md5=md5,
            rel_path=rel2,
            upload_source="gear_image",
            original_name="concurrent2.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()
        assert r1.user_id == uid1
        assert r2.user_id == uid2
        assert r1.id != r2.id  # 不同用户，不同记录
        assert r1.ref_count == 1
        assert r2.ref_count == 1

    def test_ref_count_increment_isolation(self, test_db):
        """同用户秒传递增不影响不同用户的记录"""
        from app.services.file_service import get_or_create_file

        content = b"hello-world"
        md5 = hashlib.md5(content).hexdigest()
        uid1 = _next_uid()
        uid2 = _next_uid()
        rel = _write_upload_file("gears/shared/isolation.jpg", content)

        r1, _ = get_or_create_file(
            test_db,
            user_id=uid1,
            md5=md5,
            rel_path=rel,
            upload_source="gear_image",
            original_name="isolation.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()  # flush (autoflush=False)
        r2, _ = get_or_create_file(
            test_db,
            user_id=uid2,
            md5=md5,
            rel_path=f"gears/{uid2}/isolation2.jpg",
            upload_source="gear_image",
            original_name="isolation2.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()  # flush before next query
        # uid1 秒传自己的第二次
        get_or_create_file(
            test_db,
            user_id=uid1,
            md5=md5,
            rel_path=f"gears/{uid1}/iso-again.jpg",
            upload_source="gear_image",
            original_name="iso-again.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()
        test_db.refresh(r1)
        test_db.refresh(r2)
        assert r1.ref_count == 2  # uid1 递增
        assert r2.ref_count == 1  # uid2 不受影响

    def test_delete_does_not_break_other_users(self, test_db):
        """删除一条记录不影响其他用户的同 MD5 记录"""
        from app.services.file_service import decrement_ref_count, get_or_create_file

        content = b"hello-world"
        md5 = hashlib.md5(content).hexdigest()
        uid1 = _next_uid()
        uid2 = _next_uid()
        rel = _write_upload_file("gears/shared/delete-test.jpg", content)

        _r1, _ = get_or_create_file(
            test_db,
            user_id=uid1,
            md5=md5,
            rel_path=rel,
            upload_source="gear_image",
            original_name="delete-test.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()  # flush (autoflush=False)
        _r2, _ = get_or_create_file(
            test_db,
            user_id=uid2,
            md5=md5,
            rel_path=f"gears/{uid2}/delete-test2.jpg",
            upload_source="gear_image",
            original_name="delete-test2.jpg",
            size_bytes=len(content),
            mime_type="image/jpeg",
        )
        test_db.commit()

        decremented = decrement_ref_count(test_db, user_id=uid1, rel_path=rel)
        assert decremented == 1

        user2_record = (
            test_db.query(File)
            .filter(
                File.user_id == uid2,
                File.deleted_at.is_(None),
            )
            .first()
        )
        assert user2_record is not None
