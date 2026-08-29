"""118 分析流水线分步更新集成测试（自包含，避免污染共享 fixture）。

覆盖：init → upload(analysis_id) → ai.analyze(analysis_id) → pose.analyze(analysis_id)
→ finalize(PUT)。ffmpeg / mediapipe 为外部依赖，测试中以 monkeypatch 替换为落盘桩，
避免环境依赖，聚焦验证「analysis_id 全程贯穿 + 列定向更新 + analysis_video_info 登记」。

本文件自带 Client / DB fixture，不依赖 conftest 的 session 级 _app_client，
以免与 admin 模块级 fixture 的 dependency_overrides 互相污染。
"""

import json
import os
import shutil

import pytest

from app.core.config import settings
from app.models.analysis import Analysis
from app.models.analysis_video_info import AnalysisVideoInfo
from app.models.file import File
from app.services import pose_service, video_service


def _upload_dir(user_id: int = 1) -> str:
    return os.path.join(settings.UPLOAD_DIR, "videos", str(user_id))


def _fake_process_video(abs_path: str, mode, hit_time, cuts=None):
    """落盘桩：写两帧抽帧图 + 一个 working 短片，返回与真实 process_video 同构的结果"""
    base = os.path.splitext(abs_path)[0]
    working = f"{base}_working.mp4"
    shutil.copyfile(abs_path, working)

    frame_urls = []
    for i in range(2):
        fpath = f"{base}_f{i}.jpg"
        with open(fpath, "wb") as f:
            f.write(b"\xff\xd8fakejpeg\xff\xd9")
        frame_urls.append(os.path.relpath(fpath, settings.UPLOAD_DIR))

    return {
        "frames": ["data:image/jpeg;base64,AAAA"] * 2,
        "frame_urls": frame_urls,
        "duration": 5.0,
        "thumbnail": frame_urls[0],
        "video_url": os.path.relpath(working, settings.UPLOAD_DIR),
        "working_path": working,
        "segments": None,
        "hit_time": hit_time,
        "mirage": False,
    }


def _fake_pose_analyze_frames(
    frames=None,
    video_url=None,
    save_skeleton=False,
    duration=None,
    frame_rate=None,
    full_frames=None,
    frame_urls=None,
):
    """落盘桩：写骨架帧/视频/封面到磁盘，返回与真实 analyze_frames 同构的结果"""
    if frame_urls:
        base_dir = os.path.dirname(os.path.join(settings.UPLOAD_DIR, frame_urls[0]))
    else:
        base_dir = _upload_dir()
    os.makedirs(base_dir, exist_ok=True)

    skeleton_frames = []
    for i in range(2):
        fpath = os.path.join(base_dir, f"sk_{i}.jpg")
        with open(fpath, "wb") as f:
            f.write(b"\xff\xd8skeleton\xff\xd9")
        skeleton_frames.append(os.path.relpath(fpath, settings.UPLOAD_DIR))

    video_path = os.path.join(base_dir, "skeleton.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake-skeleton-video")
    skeleton_video_url = os.path.relpath(video_path, settings.UPLOAD_DIR)

    thumb_path = os.path.join(base_dir, "sk_thumb.jpg")
    with open(thumb_path, "wb") as f:
        f.write(b"\xff\xd8skeleton-thumb\xff\xd9")
    skeleton_thumb = os.path.relpath(thumb_path, settings.UPLOAD_DIR)

    return {
        "frames": [{"landmarks": []} for _ in range(2)],
        "metrics": {"elbowAngle": 96.4, "kneeAngle": 147.5, "trunkLean": -4.4},
        "detected": True,
        "skeleton_frames": skeleton_frames,
        "skeleton_video_url": skeleton_video_url,
        "skeleton_thumb": skeleton_thumb,
    }


@pytest.fixture
def pipeline_mocks(monkeypatch):
    monkeypatch.setattr(video_service, "process_video", _fake_process_video)
    monkeypatch.setattr(pose_service, "is_available", lambda: True)
    monkeypatch.setattr(pose_service, "analyze_frames", _fake_pose_analyze_frames)
    import app.services.content_security as cs

    monkeypatch.setattr(cs, "check_media_sync", lambda *a, **k: {})
    return {}


class TestAnalysisPipeline:
    """init → upload → ai → pose → finalize 全链路"""

    def test_full_pipeline(self, auth_client, test_db, pipeline_mocks):
        # 步骤1：init
        resp = auth_client.post(
            "/api/analyses/init", json={"date": "2026-08-20", "kind": "正手", "mode": "single"}
        )
        assert resp.status_code == 200
        aid = resp.json()["data"]["id"]
        assert aid > 0

        # 准备一个上传用的小视频文件
        upload_dir = _upload_dir()
        os.makedirs(upload_dir, exist_ok=True)
        src = os.path.join(upload_dir, "src.mp4")
        with open(src, "wb") as f:
            f.write(b"fake-video-bytes")

        # 步骤2：upload(analysis_id)
        with open(src, "rb") as fh:
            resp = auth_client.post(
                "/api/video/upload",
                files={"file": ("src.mp4", fh, "video/mp4")},
                data={"mode": "single", "kind": "正手", "analysis_id": aid},
            )
        assert resp.status_code == 200
        up = resp.json()["data"]
        assert up["video_url"]
        assert len(up["frame_urls"]) == 2

        # 步骤3：ai.analyze(analysis_id)
        resp = auth_client.post(
            "/api/ai/analyze",
            json={
                "frame_urls": up["frame_urls"],
                "kind": "正手",
                "mode": "single",
                "analysis_id": aid,
            },
        )
        assert resp.status_code == 200
        ai_report = resp.json()["data"]
        assert "score" in ai_report

        # 步骤4：pose.analyze(analysis_id)
        resp = auth_client.post(
            "/api/pose/analyze",
            json={"frame_urls": up["frame_urls"], "save_skeleton": True, "analysis_id": aid},
        )
        assert resp.status_code == 200
        pose_result = resp.json()["data"]
        assert pose_result["detected"] is True

        # 步骤5：finalize(PUT) → status=completed + 完整记录
        resp = auth_client.put(f"/api/analyses/{aid}", json={"status": "completed"})
        assert resp.status_code == 200
        final = resp.json()["data"]
        assert final["status"] == "completed"

        # 数据库侧核对：分析记录齐备
        analysis = test_db.query(Analysis).filter(Analysis.id == aid).first()
        assert analysis is not None
        assert analysis.video_url == up["video_url"]
        assert analysis.report is not None
        assert analysis.pose is not None
        assert analysis.thumb is not None

        # analysis_video_info 已登记且 analysis_id 正确
        info = test_db.query(AnalysisVideoInfo).filter(AnalysisVideoInfo.analysis_id == aid).first()
        assert info is not None
        assert info.source_file_id is not None
        assert info.playback_file_id is not None
        derivatives = json.loads(info.derivatives) if info.derivatives else []
        kinds = {d["kind"] for d in derivatives}
        assert "playback" in kinds
        assert "frame" in kinds
        # 步骤4 追加了骨架衍生
        assert "skeleton" in kinds

        # 骨架文件已登记为 File（business_type=analysis）
        sk = (
            test_db.query(File)
            .filter(File.upload_source == "skeleton", File.business_id == aid)
            .all()
        )
        assert len(sk) >= 1

    def test_finalize_without_video_url_stays_processing(self, auth_client, test_db):
        """video_url 为空（步骤2 失败）时 finalize 不置 completed（遗留孤儿，不清理）"""
        resp = auth_client.post(
            "/api/analyses/init", json={"date": "2026-08-20", "kind": "综合", "mode": "single"}
        )
        aid = resp.json()["data"]["id"]
        resp = auth_client.put(f"/api/analyses/{aid}", json={"status": "completed"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "processing"
        analysis = test_db.query(Analysis).filter(Analysis.id == aid).first()
        assert analysis.status == "processing"

    def test_ai_analyze_invalid_analysis(self, auth_client):
        """analysis_id 越权/不存在 → 不落库，返回 success=False"""
        resp = auth_client.post(
            "/api/ai/analyze",
            json={"kind": "正手", "mode": "single", "analysis_id": 999999},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_init_then_legacy_create_still_works(self, auth_client, test_db):
        """向后兼容：旧 POST /api/analyses 全量创建仍置 completed（不破坏既有测试）"""
        payload = {
            "date": "2026-08-20",
            "kind": "正手",
            "mode": "single",
            "score": 80,
            "summary": "稳定",
            "ntrp": "3.5",
            "video_url": "videos/1/legacy.mp4",
        }
        resp = auth_client.post("/api/analyses", json=payload)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "completed"
