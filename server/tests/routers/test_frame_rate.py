"""视频帧率探测与骨骼视频帧率自适应测试

测试 probe_frame_rate、process_video 返回 frame_rate、analyze_frames 使用 frame_rate
"""

import pytest

from app.services import video_service

# ==================== 服务层单测：probe_frame_rate ====================


class TestProbeFrameRate:
    """probe_frame_rate 视频帧率探测"""

    def _fake_run_ffprobe(self, frame_rate: str):
        """构造 ffprobe 成功返回的 subprocess.run mock"""

        class FakeCompleted:
            returncode = 0
            stdout = f"{frame_rate}\n".encode()
            stderr = b""

        return lambda cmd, **kwargs: FakeCompleted()

    def test_ffprobe_integer_fps(self, monkeypatch):
        """ffprobe 返回整数帧率 '30' → 30.0"""
        fake = self._fake_run_ffprobe("30")
        monkeypatch.setattr(
            video_service.shutil,
            "which",
            lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
        )
        monkeypatch.setattr(video_service.subprocess, "run", fake)
        assert video_service.probe_frame_rate("/tmp/v.mp4") == 30.0

    def test_ffprobe_rational_fps(self, monkeypatch):
        """ffprobe 返回分数帧率 '30000/1001' → 约 29.97"""
        fake = self._fake_run_ffprobe("30000/1001")
        monkeypatch.setattr(
            video_service.shutil,
            "which",
            lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
        )
        monkeypatch.setattr(video_service.subprocess, "run", fake)
        assert video_service.probe_frame_rate("/tmp/v.mp4") == pytest.approx(29.97, abs=0.01)

    def test_ffprobe_60fps(self, monkeypatch):
        """ffprobe 返回 '60' → 60.0"""
        fake = self._fake_run_ffprobe("60")
        monkeypatch.setattr(
            video_service.shutil,
            "which",
            lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
        )
        monkeypatch.setattr(video_service.subprocess, "run", fake)
        assert video_service.probe_frame_rate("/tmp/v.mp4") == 60.0

    def test_no_ffprobe_returns_default(self, monkeypatch):
        """无 ffprobe → 返回默认值 30.0"""
        monkeypatch.setattr(video_service.shutil, "which", lambda name: None)
        assert video_service.probe_frame_rate("/tmp/v.mp4") == 30.0

    def test_ffprobe_error_returns_default(self, monkeypatch):
        """ffprobe 返回错误 → 返回默认值 30.0"""

        class FakeCompleted:
            returncode = 1
            stdout = b""
            stderr = b"error"

        monkeypatch.setattr(
            video_service.shutil,
            "which",
            lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
        )
        monkeypatch.setattr(video_service.subprocess, "run", lambda cmd, **kwargs: FakeCompleted())
        assert video_service.probe_frame_rate("/tmp/v.mp4") == 30.0

    def test_ffprobe_unparseable_returns_default(self, monkeypatch):
        """ffprobe 返回无法解析的字符串 → 返回默认值 30.0"""
        fake = self._fake_run_ffprobe("invalid")
        monkeypatch.setattr(
            video_service.shutil,
            "which",
            lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
        )
        monkeypatch.setattr(video_service.subprocess, "run", fake)
        assert video_service.probe_frame_rate("/tmp/v.mp4") == 30.0


# ==================== 服务层单测：process_video 返回 frame_rate ====================


class TestProcessVideoFrameRate:
    """process_video 返回值包含 frame_rate 字段"""

    def test_process_video_returns_frame_rate(self, monkeypatch, tmp_path):
        """正常流程 → 返回值包含 frame_rate"""
        video_dir = tmp_path / "videos" / "1"
        video_dir.mkdir(parents=True)
        video_path = video_dir / "test.mp4"
        video_path.write_bytes(b"fake-video")

        monkeypatch.setattr(video_service, "probe_duration", lambda p: 8.0)
        monkeypatch.setattr(video_service, "probe_frame_rate", lambda p: 29.97)
        monkeypatch.setattr(video_service, "find_ffmpeg", lambda: "/usr/bin/ffmpeg")
        monkeypatch.setattr(
            video_service,
            "extract_frames",
            lambda path, times, **kw: [b"\xff\xd8f" + bytes([i]) for i in range(len(times))],
        )
        monkeypatch.setattr(video_service.settings, "UPLOAD_DIR", str(tmp_path))
        result = video_service.process_video(str(video_path), "single", 2.0)
        assert "frame_rate" in result
        assert result["frame_rate"] == 29.97

    def test_process_video_frame_rate_default(self, monkeypatch, tmp_path):
        """probe_frame_rate 失败 → frame_rate 为默认值 30.0"""
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
        assert result["frame_rate"] == 30.0


# ==================== 服务层单测：analyze_frames 使用 frame_rate ====================


class TestAnalyzeFramesFrameRate:
    """analyze_frames 使用 frame_rate 计算骨骼视频帧率"""

    FAKE_LMS = [{"x": 0.5, "y": 0.3, "z": 0.0, "visibility": 0.9} for _ in range(33)]

    def _fake_frame(self) -> str:
        """真实 JPEG 的 base64 dataURL"""
        import base64
        import io

        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (64, 64), (120, 120, 120)).save(buf, format="JPEG")
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    def _setup_video(self, data_dir, uid=1, name="abc.mp4"):
        """在隔离 UPLOAD_DIR 下构造 videos/{uid}/{name}，返回绝对路径"""
        video_dir = data_dir / "uploads" / "videos" / str(uid)
        video_dir.mkdir(parents=True, exist_ok=True)
        video_path = video_dir / name
        video_path.write_bytes(b"fake-video")
        return video_path

    def test_analyze_frames_with_frame_rate(self, monkeypatch, data_dir):
        """传入 frame_rate → 骨骼视频帧率 = 帧数/时长（与原始视频播放速度一致）"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: self.FAKE_LMS)

        received_fps = []

        def fake_encode(paths, out, fps):
            received_fps.append(fps)

            with open(out, "wb") as f:
                f.write(b"mp4")
            return True

        monkeypatch.setattr(ps, "encode_skeleton_video", fake_encode)
        self._setup_video(data_dir)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))

        # 传入 frame_rate=30.0，duration=10.0，2 帧
        # 期望 fps = 2/10.0 = 0.2（播放时长与原视频一致）
        ps.analyze_frames(
            [self._fake_frame(), self._fake_frame()],
            video_url="videos/1/abc.mp4",
            save_skeleton=True,
            duration=10.0,
            frame_rate=30.0,
        )
        assert len(received_fps) == 1
        assert received_fps[0] == 0.2

    def test_analyze_frames_high_frame_rate(self, monkeypatch, data_dir):
        """高帧率视频（60fps）→ 骨骼视频帧率 = 帧数/时长"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: self.FAKE_LMS)

        received_fps = []

        def fake_encode(paths, out, fps):
            received_fps.append(fps)

            with open(out, "wb") as f:
                f.write(b"mp4")
            return True

        monkeypatch.setattr(ps, "encode_skeleton_video", fake_encode)
        self._setup_video(data_dir)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))

        # 传入 frame_rate=60.0，duration=10.0，2 帧
        # 期望 fps = 2/10.0 = 0.2（播放时长与原视频一致）
        ps.analyze_frames(
            [self._fake_frame(), self._fake_frame()],
            video_url="videos/1/abc.mp4",
            save_skeleton=True,
            duration=10.0,
            frame_rate=60.0,
        )
        assert received_fps[0] == 0.2

    def test_analyze_frames_without_frame_rate(self, monkeypatch, data_dir):
        """未传入 frame_rate → 使用 帧数/时长 计算"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: self.FAKE_LMS)

        received_fps = []

        def fake_encode(paths, out, fps):
            received_fps.append(fps)

            with open(out, "wb") as f:
                f.write(b"mp4")
            return True

        monkeypatch.setattr(ps, "encode_skeleton_video", fake_encode)
        self._setup_video(data_dir)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))

        # 未传入 frame_rate，duration=10.0，2 帧
        # 期望 fps = 2/10.0 = 0.2
        ps.analyze_frames(
            [self._fake_frame(), self._fake_frame()],
            video_url="videos/1/abc.mp4",
            save_skeleton=True,
            duration=10.0,
        )
        assert received_fps[0] == 0.2

    def test_analyze_frames_low_frame_rate(self, monkeypatch, data_dir):
        """低帧率视频（15fps）→ 骨骼视频帧率 = 帧数/时长"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: self.FAKE_LMS)

        received_fps = []

        def fake_encode(paths, out, fps):
            received_fps.append(fps)

            with open(out, "wb") as f:
                f.write(b"mp4")
            return True

        monkeypatch.setattr(ps, "encode_skeleton_video", fake_encode)
        self._setup_video(data_dir)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))

        # 传入 frame_rate=15.0，duration=10.0，2 帧
        # 期望 fps = 2/10.0 = 0.2（播放时长与原视频一致）
        ps.analyze_frames(
            [self._fake_frame(), self._fake_frame()],
            video_url="videos/1/abc.mp4",
            save_skeleton=True,
            duration=10.0,
            frame_rate=15.0,
        )
        assert received_fps[0] == 0.2


# ==================== 接口测试：POST /api/pose/analyze 接收 frame_rate ====================


class TestPoseAnalyzeFrameRate:
    """测试 /api/pose/analyze 接收 frame_rate 参数"""

    VALID_PAYLOAD = {"frames": ["data:image/jpeg;base64,/9j/4AAQSkZJRg=="]}

    FAKE_RESULT = {
        "frames": [
            {"landmarks": [{"x": 0.5, "y": 0.3, "z": 0.0, "visibility": 0.9} for _ in range(33)]}
        ],
        "metrics": {"elbowAngle": 95.2, "kneeAngle": 140.1, "trunkLean": 8.3},
        "detected": True,
    }

    def test_analyze_with_frame_rate(self, auth_client, monkeypatch):
        """传入 frame_rate → 200 + 正常响应"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)

        received_kwargs = {}

        def fake_analyze(
            frames, video_url=None, save_skeleton=False, duration=None, frame_rate=None
        ):
            received_kwargs["frame_rate"] = frame_rate
            return self.FAKE_RESULT

        monkeypatch.setattr(pose_router.pose_service, "analyze_frames", fake_analyze)
        payload = {**self.VALID_PAYLOAD, "frame_rate": 29.97}
        response = auth_client.post("/api/pose/analyze", json=payload)
        assert response.status_code == 200
        assert received_kwargs["frame_rate"] == 29.97

    def test_analyze_without_frame_rate(self, auth_client, monkeypatch):
        """未传入 frame_rate → frame_rate=None"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)

        received_kwargs = {}

        def fake_analyze(
            frames, video_url=None, save_skeleton=False, duration=None, frame_rate=None
        ):
            received_kwargs["frame_rate"] = frame_rate
            return self.FAKE_RESULT

        monkeypatch.setattr(pose_router.pose_service, "analyze_frames", fake_analyze)
        response = auth_client.post("/api/pose/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        assert received_kwargs["frame_rate"] is None

    def test_analyze_with_all_params(self, auth_client, monkeypatch):
        """传入所有参数 → 正常响应"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)

        received_kwargs = {}

        def fake_analyze(
            frames, video_url=None, save_skeleton=False, duration=None, frame_rate=None
        ):
            received_kwargs.update({
                "video_url": video_url,
                "save_skeleton": save_skeleton,
                "duration": duration,
                "frame_rate": frame_rate,
            })
            return self.FAKE_RESULT

        monkeypatch.setattr(pose_router.pose_service, "analyze_frames", fake_analyze)
        payload = {
            **self.VALID_PAYLOAD,
            "video_url": "videos/1/abc.mp4",
            "save_skeleton": True,
            "duration": 12.0,
            "frame_rate": 29.97,
        }
        response = auth_client.post("/api/pose/analyze", json=payload)
        assert response.status_code == 200
        assert received_kwargs["frame_rate"] == 29.97
        assert received_kwargs["duration"] == 12.0
        assert received_kwargs["video_url"] == "videos/1/abc.mp4"
        assert received_kwargs["save_skeleton"] is True
