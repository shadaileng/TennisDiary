"""POST /api/video/upload 视频上传与抽帧接口测试"""

import pytest

from app.services import video_service
from app.services.video_service import FfmpegUnavailableError, VideoTooLongError

# ==================== 服务层单测 ====================


class TestBuildSamplingTimes:
    """build_sampling_times 采样时间点"""

    def test_single_7_frames(self):
        """single 模式 → 7 帧，clamp 在 [0.01, duration-0.01]"""
        times = video_service.build_sampling_times("single", 10.0, 2.0)
        assert len(times) == 7
        assert all(0.01 <= t <= 9.99 for t in times)
        # 命中点附近应有 0 偏移帧
        assert min(times, key=lambda t: abs(t - 2.0)) == 2.0

    def test_single_clamp_negative(self):
        """single hit 在开头 → 负偏移 clamp 到 0.01"""
        times = video_service.build_sampling_times("single", 5.0, 0.2)
        assert all(t >= 0.01 for t in times)

    def test_full_8_frames_uniform(self):
        """full 模式 → 8 帧均匀分布"""
        times = video_service.build_sampling_times("full", 16.0, 8.0)
        assert len(times) == 8
        assert times == [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0]

    def test_no_hit_time_defaults_mid(self):
        """无 hit_time → 缺省为 duration/2"""
        times = video_service.build_sampling_times("single", 10.0, None)
        assert min(times, key=lambda t: abs(t - 5.0)) == 5.0


class TestProbeDuration:
    """probe_duration 视频时长探测"""

    def _fake_run_ffprobe(self, duration):
        """构造 ffprobe 成功返回的 subprocess.run mock"""

        class FakeCompleted:
            returncode = 0
            stdout = f"{duration}\n".encode()
            stderr = b""

        return lambda cmd, **kwargs: FakeCompleted()

    def test_ffprobe_success(self, monkeypatch):
        """ffprobe 可用 → 返回时长"""
        fake = self._fake_run_ffprobe("8.5")
        monkeypatch.setattr(
            video_service.shutil,
            "which",
            lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
        )
        monkeypatch.setattr(video_service.subprocess, "run", fake)
        assert video_service.probe_duration("/tmp/v.mp4") == 8.5

    def test_fallback_ffmpeg_stderr(self, monkeypatch):
        """无 ffprobe → 解析 ffmpeg stderr Duration 行"""

        class FakeCompleted:
            returncode = 0
            stdout = b""

            @property
            def stderr(self):
                return b"  Duration: 00:00:04.30, start: 0.000000, bitrate: 1234 kb/s\n"

        monkeypatch.setattr(video_service.shutil, "which", lambda name: None)
        monkeypatch.setattr(video_service.subprocess, "run", lambda cmd, **kwargs: FakeCompleted())
        assert video_service.probe_duration("/tmp/v.mp4") == pytest.approx(4.3, abs=0.01)

    def test_unparseable_raises(self, monkeypatch):
        """无法解析 → 抛 ValueError"""

        class FakeCompleted:
            returncode = 1
            stdout = b""
            stderr = b"error"

        monkeypatch.setattr(video_service.shutil, "which", lambda name: None)
        monkeypatch.setattr(video_service.subprocess, "run", lambda cmd, **kwargs: FakeCompleted())
        with pytest.raises(ValueError):
            video_service.probe_duration("/tmp/v.mp4")


class TestExtractFrames:
    """extract_frames 抽帧命令"""

    def test_calls_ffmpeg_per_frame(self, monkeypatch):
        """每帧一次 ffmpeg 调用，含 -ss / -frames:v 1 / scale=640"""
        calls: list[list[str]] = []

        class FakeCompleted:
            returncode = 0
            stdout = b"\xff\xd8fakejpeg"
            stderr = b""

            def __init__(self, *args, **kwargs):
                pass

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return FakeCompleted()

        monkeypatch.setattr(video_service.subprocess, "run", fake_run)
        frames = video_service.extract_frames("/tmp/v.mp4", [0.5, 1.5], width=640)
        assert len(frames) == 2
        assert len(calls) == 2
        first = " ".join(calls[0])
        assert "-ss" in first
        assert "0.5" in first
        assert "-frames:v" in first
        assert "scale=640" in first


class TestProcessVideoLimits:
    """process_video 时长限制"""

    def test_single_too_long(self, monkeypatch):
        """single 20s > 15s → 抛 VideoTooLongError"""
        monkeypatch.setattr(video_service, "probe_duration", lambda p: 20.0)
        with pytest.raises(VideoTooLongError):
            video_service.process_video("/tmp/v.mp4", "single", 2.0)

    def test_full_too_long(self, monkeypatch):
        """full 100s > 90s → 抛 VideoTooLongError"""
        monkeypatch.setattr(video_service, "probe_duration", lambda p: 100.0)
        with pytest.raises(VideoTooLongError):
            video_service.process_video("/tmp/v.mp4", "full", 40.0)

    def test_ffmpeg_missing(self, monkeypatch):
        """无 ffmpeg → 抛 FfmpegUnavailableError"""
        monkeypatch.setattr(video_service, "probe_duration", lambda p: 5.0)
        monkeypatch.setattr(video_service, "find_ffmpeg", lambda: None)
        with pytest.raises(FfmpegUnavailableError):
            video_service.process_video("/tmp/v.mp4", "single", 1.0)

    def test_process_success(self, monkeypatch, tmp_path):
        """正常流程 → 返回帧 + duration + thumbnail"""
        video_dir = tmp_path / "videos" / "1"
        video_dir.mkdir(parents=True)
        video_path = video_dir / "test.mp4"
        video_path.write_bytes(b"fake-video")

        monkeypatch.setattr(video_service, "probe_duration", lambda p: 8.0)
        monkeypatch.setattr(video_service, "probe_frame_rate", lambda p: 30.0)
        monkeypatch.setattr(video_service, "find_ffmpeg", lambda: "/usr/bin/ffmpeg")
        monkeypatch.setattr(
            video_service,
            "extract_frames",
            lambda path, times, **kw: [b"\xff\xd8f" + bytes([i]) for i in range(len(times))],
        )
        monkeypatch.setattr(video_service.settings, "UPLOAD_DIR", str(tmp_path))
        result = video_service.process_video(str(video_path), "single", 2.0)
        assert result["duration"] == 8.0
        assert result["frame_rate"] == 30.0
        assert len(result["frames"]) == 7  # single 采样 7 帧
        assert result["thumbnail"].startswith("data:image/jpeg;base64,")  # 封面帧转 dataURL
        assert result["hit_time"] == 2.0


# ==================== 接口测试 ====================


class TestVideoUpload:
    """测试 /api/video/upload"""

    def test_upload_success(self, auth_client, data_dir, monkeypatch):
        """成功 → 200 + frames 数组（base64 dataURL）"""
        from app.routers import video as video_router

        fake_result = {
            "frames": ["data:image/jpeg;base64,ZmFrZQ=="],
            "duration": 8.0,
            "thumbnail": "data:image/jpeg;base64,dGh1bWI=",
            "hit_time": 2.0,
        }
        monkeypatch.setattr(
            video_router.video_service, "process_video", lambda path, mode, hit_time: fake_result
        )
        files = {"file": ("swing.mp4", b"fake-video-bytes", "video/mp4")}
        data = {"mode": "single", "kind": "正手", "hit_time": "2.0"}
        response = auth_client.post("/api/video/upload", files=files, data=data)
        assert response.status_code == 200
        body = response.json()["data"]
        assert len(body["frames"]) == 1
        assert body["frames"][0].startswith("data:image/jpeg;base64,")
        assert body["duration"] == 8.0
        assert body["thumbnail"].startswith("data:image/jpeg;base64,")

    def test_upload_wrong_type(self, auth_client, data_dir, monkeypatch):
        """非视频类型 → 400"""
        from app.routers import video as video_router

        monkeypatch.setattr(
            video_router.video_service, "process_video", lambda path, mode, hit_time: {}
        )
        files = {"file": ("img.png", b"png-bytes", "image/png")}
        response = auth_client.post("/api/video/upload", files=files, data={"mode": "single"})
        assert response.status_code == 400

    def test_upload_no_ffmpeg(self, auth_client, data_dir, monkeypatch):
        """ffmpeg 不可用 → 503"""
        from app.routers import video as video_router

        def boom(path, mode, hit_time):
            raise FfmpegUnavailableError("ffmpeg 不可用")

        monkeypatch.setattr(video_router.video_service, "process_video", boom)
        files = {"file": ("swing.mp4", b"fake", "video/mp4")}
        response = auth_client.post("/api/video/upload", files=files, data={"mode": "single"})
        assert response.status_code == 503

    def test_upload_requires_auth(self, client, data_dir):
        """未登录 → 401/403"""
        files = {"file": ("swing.mp4", b"fake", "video/mp4")}
        response = client.post("/api/video/upload", files=files, data={"mode": "single"})
        assert response.status_code in (401, 403)
