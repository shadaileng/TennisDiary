"""文件登记 MIME 兜底与分类源补全测试（Step 131）

覆盖：
- `mime_type_from_ext` / `resolve_mime_type` 纯函数（fast）
- `get_or_create_file` / `batch_get_or_create_files` / `register_orphan_files` 登记兜底
- 骨架类 `upload_source` 在分类逻辑中按 Analysis 路径匹配（不再误判未绑定业务）
"""

import hashlib
import json
import time

import pytest

from app.models.analysis import Analysis
from app.models.file import File
from app.services import file_service

# ==================== 纯函数（fast） ====================


@pytest.mark.fast
class TestMimeTypeFromExt:
    """mime_type_from_ext：仅按扩展名映射，无磁盘 I/O"""

    def test_jpg(self):
        from app.core.mime import mime_type_from_ext

        assert mime_type_from_ext("videos/1/1788331858328_8f1245f6_seg0_thumb.jpg") == "image/jpeg"

    def test_mp4(self):
        from app.core.mime import mime_type_from_ext

        assert mime_type_from_ext("videos/1/xxx_skeleton.mp4") == "video/mp4"

    def test_unknown_ext(self):
        from app.core.mime import mime_type_from_ext

        assert mime_type_from_ext("videos/1/unknown.bin") == ""


@pytest.mark.fast
class TestResolveMimeType:
    """resolve_mime_type：调用方优先 / 探测 / 零 I/O 模式"""

    def test_respects_caller_value(self):
        """传入非空 mime 时不被覆盖（上传端点已做服务端探测）"""
        assert (
            file_service.resolve_mime_type("/not/exist/x.jpg", "avatar", "image/png") == "image/png"
        )

    def test_probe_fills_jpg(self, tmp_path):
        """空值时探测；假内容 .jpg 由 PIL 失败回退扩展名 → image/jpeg"""
        path = tmp_path / "seg0_thumb.jpg"
        path.write_bytes(b"not-a-real-jpeg")

        assert file_service.resolve_mime_type(str(path), "skeleton_thumb") == "image/jpeg"

    def test_probe_fills_mp4(self, tmp_path):
        """骨架视频（.mp4）探测结果恒为 video/mp4（ffprobe 缺失时回退扩展名）"""
        path = tmp_path / "seg0_skeleton.mp4"
        path.write_bytes(b"not-a-real-mp4")

        assert file_service.resolve_mime_type(str(path), "skeleton_video") == "video/mp4"

    def test_no_probe_skips_detection(self, tmp_path, monkeypatch):
        """probe=False：不做任何探测（零 I/O），仅用扩展名映射"""

        def _boom(*_args, **_kwargs):
            raise AssertionError("probe=False 不应触发探测")

        monkeypatch.setattr(file_service, "detect_mime_type", _boom)

        assert (
            file_service.resolve_mime_type("/not/exist/x.jpg", "skeleton_thumb", probe=False)
            == "image/jpeg"
        )

    def test_empty_path_returns_empty(self):
        assert file_service.resolve_mime_type(None, "skeleton") == ""


@pytest.mark.fast
class TestInferFileSource:
    """analyses._infer_file_source：报告落库 upload_source 细化"""

    def test_video_url(self):
        from app.routers.analyses import _infer_file_source

        assert _infer_file_source("videos/1/a.mp4", "videos/1/a.mp4", None) == "video"

    def test_analysis_thumb(self):
        from app.routers.analyses import _infer_file_source

        assert _infer_file_source("videos/1/t.jpg", "videos/1/a.mp4", "videos/1/t.jpg") == (
            "analysis_thumb"
        )

    def test_skeleton_video(self):
        from app.routers.analyses import _infer_file_source

        source = _infer_file_source("videos/1/a_skeleton.mp4", "videos/1/a.mp4", None)
        assert source == "skeleton_video"

    def test_skeleton_thumb(self):
        from app.routers.analyses import _infer_file_source

        source = _infer_file_source("videos/1/a_thumb.jpg", "videos/1/a.mp4", None)
        assert source == "skeleton_thumb"

    def test_skeleton_frame(self):
        from app.routers.analyses import _infer_file_source

        source = _infer_file_source("videos/1/a_sk001.jpg", "videos/1/a.mp4", None)
        assert source == "skeleton_frame"


# ==================== 登记兜底（DB） ====================


class TestGetOrCreateFileMime:
    """get_or_create_file：调用方未传 mime 时自动补齐"""

    def test_fills_jpg_mime(self, test_db, tmp_path):
        from app.services.file_service import get_or_create_file

        path = tmp_path / "seg0_thumb.jpg"
        path.write_bytes(b"fake-jpeg-bytes")

        record, _ = get_or_create_file(
            db=test_db,
            user_id=1,
            rel_path="videos/1/seg0_thumb.jpg",
            abs_path=str(path),
            upload_source="skeleton_thumb",
            original_name="seg0_thumb.jpg",
        )

        assert record.mime_type == "image/jpeg"

    def test_fills_mp4_mime(self, test_db, tmp_path):
        from app.services.file_service import get_or_create_file

        path = tmp_path / "seg0_skeleton.mp4"
        path.write_bytes(b"fake-mp4-bytes")

        record, _ = get_or_create_file(
            db=test_db,
            user_id=1,
            rel_path="videos/1/seg0_skeleton.mp4",
            abs_path=str(path),
            upload_source="skeleton_video",
            original_name="seg0_skeleton.mp4",
        )

        assert record.mime_type == "video/mp4"

    def test_keeps_caller_mime(self, test_db, tmp_path):
        """调用方传入准确值时不被探测覆盖"""
        from app.services.file_service import get_or_create_file

        path = tmp_path / "clip.mp4"
        path.write_bytes(b"fake-mp4-bytes")

        record, _ = get_or_create_file(
            db=test_db,
            user_id=1,
            rel_path="videos/1/clip.mp4",
            abs_path=str(path),
            upload_source="video",
            original_name="clip.mp4",
            mime_type="video/quicktime",
        )

        assert record.mime_type == "video/quicktime"

    def test_reuse_fills_empty_mime(self, test_db, data_dir):
        """秒传命中且存量记录 mime 为空时，新记录补齐探测值（不扩散空值）"""
        from app.services.file_service import get_or_create_file

        content = b"shared-video-bytes"
        md5 = hashlib.md5(content).hexdigest()
        rel_old = "videos/1/old.mp4"
        old_abs = data_dir / "uploads" / "videos" / "1"
        old_abs.mkdir(parents=True, exist_ok=True)
        (old_abs / "old.mp4").write_bytes(content)

        # 存量记录：mime_type 为空（131 修复前落库的数据）
        test_db.add(
            File(
                user_id=1,
                md5=md5,
                original_name="old.mp4",
                rel_path=rel_old,
                size_bytes=len(content),
                mime_type="",
                upload_source="video",
                ref_count=1,
                created_at=time.time(),
            )
        )
        test_db.flush()

        new_file = old_abs / "new.mp4"
        new_file.write_bytes(content)
        record, is_reuse = get_or_create_file(
            db=test_db,
            user_id=1,
            rel_path="videos/1/new.mp4",
            abs_path=str(new_file),
            upload_source="video_playback",
            original_name="new.mp4",
        )

        assert is_reuse is True
        assert record.mime_type == "video/mp4"


class TestBatchGetOrCreateFilesMime:
    """batch_get_or_create_files：扩展名映射补齐，且不做磁盘 I/O"""

    def test_fills_mime_by_ext(self, test_db):
        from app.services.file_service import batch_get_or_create_files

        records = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": "videos/1/a_skeleton.mp4",
                    "md5": hashlib.md5(b"v").hexdigest(),
                    "size": 1,
                    "upload_source": "skeleton_video",
                },
                {
                    "rel_path": "videos/1/a_thumb.jpg",
                    "md5": hashlib.md5(b"t").hexdigest(),
                    "size": 1,
                    "upload_source": "skeleton_thumb",
                },
            ],
            business_type="analysis",
            business_id=1,
        )

        by_path = {r.rel_path: r.mime_type for r in records}
        assert by_path["videos/1/a_skeleton.mp4"] == "video/mp4"
        assert by_path["videos/1/a_thumb.jpg"] == "image/jpeg"

    def test_respects_info_mime(self, test_db):
        from app.services.file_service import batch_get_or_create_files

        records = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": "videos/1/b.mov",
                    "md5": hashlib.md5(b"m").hexdigest(),
                    "size": 1,
                    "upload_source": "video_playback",
                    "mime_type": "video/quicktime",
                }
            ],
        )

        assert records[0].mime_type == "video/quicktime"

    def test_no_disk_io(self, test_db, monkeypatch):
        """批量登记不得触发探测（121 优化：写表路径零磁盘 I/O）"""

        def _boom(*_args, **_kwargs):
            raise AssertionError("批量登记不应触发 MIME 探测")

        monkeypatch.setattr(file_service, "detect_mime_type", _boom)

        records = file_service.batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": "videos/1/c_skeleton.mp4",
                    "md5": hashlib.md5(b"c").hexdigest(),
                    "size": 1,
                    "upload_source": "skeleton_video",
                }
            ],
        )

        assert records[0].mime_type == "video/mp4"


class TestRegisterOrphanFilesMime:
    """register_orphan_files：孤儿注册补齐 mime"""

    def test_fills_mime(self, test_db, data_dir):
        from app.services.file_service import register_orphan_files

        target = data_dir / "uploads" / "videos" / "1"
        target.mkdir(parents=True, exist_ok=True)
        (target / "orphan_thumb.jpg").write_bytes(b"fake-jpeg-bytes")

        records = register_orphan_files(test_db, ["videos/1/orphan_thumb.jpg"])

        assert len(records) == 1
        assert records[0].mime_type == "image/jpeg"


# ==================== 分类源补全（DB） ====================


def _make_analysis(db, user_id: int, rel: str) -> Analysis:
    """构造引用 rel 的分析记录（pose 中包含骨架路径）"""
    analysis = Analysis(
        user_id=user_id,
        date="2026-09-04",
        kind="正手",
        mode="single",
        status="completed",
        pose=json.dumps({"skeleton_video_url": rel, "skeleton_frames": []}),
        created_at=time.time(),
    )
    db.add(analysis)
    db.flush()
    return analysis


class TestClassifySkeletonSources:
    """骨架类 upload_source 在无 business_id 时按 Analysis 路径匹配"""

    @pytest.mark.parametrize(
        "source",
        ["skeleton_video", "skeleton_thumb", "skeleton_frame"],
    )
    def test_classify_file_usage_matches_analysis(self, test_db, source):
        rel = f"videos/1/a_{source}.mp4"
        _make_analysis(test_db, 1, rel)
        record = File(
            user_id=1,
            md5=hashlib.md5(source.encode()).hexdigest(),
            original_name=f"a_{source}.mp4",
            rel_path=rel,
            size_bytes=10,
            mime_type="video/mp4",
            upload_source=source,
            ref_count=1,
            created_at=time.time(),
        )
        test_db.add(record)
        test_db.flush()

        status, _reason = file_service.classify_file_usage(test_db, record)

        assert status == "in_use", f"{source} 应命中 Analysis 路径匹配"

    def test_bulk_classify_matches_analysis(self, test_db):
        rel = "videos/1/a_thumb.jpg"
        _make_analysis(test_db, 1, rel)
        record = File(
            user_id=1,
            md5=hashlib.md5(b"bulk").hexdigest(),
            original_name="a_thumb.jpg",
            rel_path=rel,
            size_bytes=10,
            mime_type="image/jpeg",
            upload_source="skeleton_thumb",
            ref_count=1,
            created_at=time.time(),
        )
        test_db.add(record)
        test_db.flush()

        result = file_service.bulk_classify_files(test_db, [record])

        assert result[record.id][0] == "in_use"
