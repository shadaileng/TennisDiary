"""118 §5.8 文件使用边界分类测试。

验证 classify 以「小程序实际消费」为边界：
- 原片 video / 抽帧 video_frame：不被直接消费 → unreferenced（可清除）
- 播放短片 video_playback / 骨架 skeleton：被 Analysis 引用 → in_use，否则 unreferenced
"""

import hashlib
import os
import tempfile
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.analysis import Analysis
from app.models.file import File
from app.services import file_service


def _insert_file(db, user_id, rel_path, upload_source, business_type=None, business_id=None):
    rec = File(
        user_id=user_id,
        md5=hashlib.md5(f"b-{rel_path}".encode()).hexdigest(),
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=42,
        mime_type="image/jpeg",
        upload_source=upload_source,
        business_type=business_type,
        business_id=business_id,
        ref_count=1,
        created_at=time.time(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_boundary_")
    os.close(fd)
    eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        eng.dispose()
        os.unlink(path)


def _classify(db, rec):
    return file_service.classify_file_usage(db, rec)


class TestUsageBoundary:
    def test_video_source_unreferenced(self, test_db):
        rel = "videos/1/a.mp4"
        test_db.add(Analysis(id=1, user_id=1, date="2026-01-01", video_url=rel))
        test_db.commit()
        rec = _insert_file(test_db, 1, rel, "video")
        status, reason = _classify(test_db, rec)
        assert status == "unreferenced"
        assert "不被小程序直接消费" in reason

    def test_video_frame_source_unreferenced(self, test_db):
        rel = "videos/1/a_f0.jpg"
        test_db.add(Analysis(id=2, user_id=1, date="2026-01-01", highlights=rel))
        test_db.commit()
        rec = _insert_file(test_db, 1, rel, "video_frame")
        status, _ = _classify(test_db, rec)
        assert status == "unreferenced"

    def test_video_playback_in_use(self, test_db):
        rel = "videos/1/a_working.mp4"
        test_db.add(Analysis(id=3, user_id=1, date="2026-01-01", video_url=rel))
        test_db.commit()
        rec = _insert_file(test_db, 1, rel, "video_playback")
        status, _ = _classify(test_db, rec)
        assert status == "in_use"

    def test_video_playback_unreferenced(self, test_db):
        # video_url 指向别的文件，playback 文件未被引用
        test_db.add(Analysis(id=4, user_id=1, date="2026-01-01", video_url="videos/1/other.mp4"))
        test_db.commit()
        rec = _insert_file(test_db, 1, "videos/1/a_working.mp4", "video_playback")
        status, _ = _classify(test_db, rec)
        assert status == "unreferenced"

    def test_skeleton_in_use(self, test_db):
        rel = "videos/1/sk0.jpg"
        test_db.add(
            Analysis(
                id=5, user_id=1, date="2026-01-01", pose='{"skeleton_frames": ["videos/1/sk0.jpg"]}'
            )
        )
        test_db.commit()
        rec = _insert_file(test_db, 1, rel, "skeleton")
        status, _ = _classify(test_db, rec)
        assert status == "in_use"

    def test_skeleton_unreferenced(self, test_db):
        rec = _insert_file(test_db, 1, "videos/1/sk0.jpg", "skeleton")
        status, _ = _classify(test_db, rec)
        assert status == "unreferenced"
