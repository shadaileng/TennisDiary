"""文件登记 MIME 兜底与分类源补全测试（Step 131 / 138 门面化）

覆盖：
- `mime_type_from_ext` 纯函数（fast）
- 门面 `mime_of` 的「调用方优先 / 探测 / 零 I/O」三种模式
- `register` / `register_batch` / `register_orphans` 的 MIME 兜底
- 骨架类 upload_source 在分类逻辑中按业务注册表匹配（不再误判未绑定业务）
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
class TestMimeOf:
    """门面 mime_of：调用方优先 / 探测 / 零 I/O 模式"""

    def _put(self, rel_path: str, content: bytes) -> None:
        file_service.write_bytes(file_service.abs_of(rel_path), content)

    def test_respects_caller_value(self):
        """传入非空 mime 时不被覆盖（上传端点已做服务端探测）"""
        assert file_service.mime_of("videos/1/x.jpg", "avatar", "image/png") == "image/png"

    def test_probe_fills_jpg(self):
        """空值时探测；假内容 .jpg 由 PIL 失败回退扩展名 → image/jpeg"""
        self._put("videos/1/seg0_thumb.jpg", b"not-a-real-jpeg")
        assert file_service.mime_of("videos/1/seg0_thumb.jpg", "skeleton_thumb") == "image/jpeg"

    def test_probe_fills_mp4(self):
        """骨架视频（.mp4）探测结果恒为 video/mp4（ffprobe 缺失时回退扩展名）"""
        self._put("videos/1/seg0_skeleton.mp4", b"not-a-real-mp4")
        assert file_service.mime_of("videos/1/seg0_skeleton.mp4", "skeleton_video") == "video/mp4"

    def test_no_probe_skips_detection(self, monkeypatch):
        """probe=False：不做任何探测（零 I/O），仅用扩展名映射"""

        def _boom(*_args, **_kwargs):
            raise AssertionError("probe=False 不应触发探测")

        monkeypatch.setattr("app.services.file_store.detect_mime_type", _boom)

        assert file_service.mime_of("videos/1/x.jpg", "skeleton_thumb", probe=False) == "image/jpeg"

    def test_empty_path_returns_empty(self):
        assert file_service.mime_of("", "skeleton") == ""


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


class TestRegisterMime:
    """register：调用方未传 mime 时自动补齐"""

    def test_fills_jpg_mime(self, test_db, tmp_path):
        path = tmp_path / "seg0_thumb.jpg"
        path.write_bytes(b"fake-jpeg-bytes")

        record, _ = file_service.register(
            db=test_db,
            user_id=1,
            src_path=str(path),
            category="skeleton_thumb",
            original_name="seg0_thumb.jpg",
        )

        assert record.mime_type == "image/jpeg"

    def test_fills_mp4_mime(self, test_db, tmp_path):
        path = tmp_path / "seg0_skeleton.mp4"
        path.write_bytes(b"fake-mp4-bytes")

        record, _ = file_service.register(
            db=test_db,
            user_id=1,
            src_path=str(path),
            category="skeleton_video",
            original_name="seg0_skeleton.mp4",
        )

        assert record.mime_type == "video/mp4"

    def test_keeps_caller_mime(self, test_db, tmp_path):
        """调用方传入准确值时不被探测覆盖"""
        path = tmp_path / "clip.mp4"
        path.write_bytes(b"fake-mp4-bytes")

        record, _ = file_service.register(
            db=test_db,
            user_id=1,
            src_path=str(path),
            category="video",
            original_name="clip.mp4",
            mime_type="video/quicktime",
        )

        assert record.mime_type == "video/quicktime"


class TestRegisterBatchMime:
    """register_batch：扩展名映射补齐，且不做磁盘探测"""

    def test_fills_mime_by_ext(self, test_db):
        records = file_service.register_batch(
            db=test_db,
            user_id=1,
            items=[
                file_service.FileDraft(
                    md5=hashlib.md5(b"v").hexdigest(),
                    size=1,
                    ext=".mp4",
                    upload_source="skeleton_video",
                    original_name="a_skeleton.mp4",
                ),
                file_service.FileDraft(
                    md5=hashlib.md5(b"t").hexdigest(),
                    size=1,
                    ext=".jpg",
                    upload_source="skeleton_thumb",
                    original_name="a_thumb.jpg",
                ),
            ],
        )

        assert records[0].mime_type == "video/mp4"
        assert records[1].mime_type == "image/jpeg"

    def test_respects_info_mime(self, test_db):
        records = file_service.register_batch(
            db=test_db,
            user_id=1,
            items=[
                file_service.FileDraft(
                    md5=hashlib.md5(b"m").hexdigest(),
                    size=1,
                    ext=".mov",
                    upload_source="video_playback",
                    original_name="b.mov",
                    mime_type="video/quicktime",
                )
            ],
        )

        assert records[0].mime_type == "video/quicktime"

    def test_no_disk_probe(self, test_db, monkeypatch):
        """批量登记不得触发探测（121 优化：写表路径零磁盘 I/O）"""

        def _boom(*_args, **_kwargs):
            raise AssertionError("批量登记不应触发 MIME 探测")

        monkeypatch.setattr("app.services.file_store.detect_mime_type", _boom)

        records = file_service.register_batch(
            db=test_db,
            user_id=1,
            items=[
                file_service.FileDraft(
                    md5=hashlib.md5(b"c").hexdigest(),
                    size=1,
                    ext=".mp4",
                    upload_source="skeleton_video",
                    original_name="c_skeleton.mp4",
                )
            ],
        )

        assert records[0].mime_type == "video/mp4"


class TestRegisterOrphansMime:
    """register_orphans：孤儿注册补齐 mime"""

    def test_fills_mime(self, test_db):
        rel = "videos/1/orphan_thumb.jpg"
        file_service.write_bytes(file_service.abs_of(rel), b"fake-jpeg-bytes")

        records = file_service.register_orphans(test_db, [rel])

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
    """骨架类 upload_source 在无 business_id 时按业务注册表匹配"""

    @pytest.mark.parametrize("source", ["skeleton_video", "skeleton_thumb", "skeleton_frame"])
    def test_classify_matches_analysis(self, test_db, source):
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
        # 物理文件需存在，否则判定为 missing
        file_service.write_bytes(file_service.abs_of(rel), b"x")

        status, _reason = file_service.classify(test_db, [record])[record.id]

        assert status == "in_use", f"{source} 应命中业务注册表匹配"
