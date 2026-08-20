"""POST /api/video/upload 视频上传与抽帧接口测试"""

import os
import subprocess

import pytest

from app.services import video_service
from app.services.video_service import (
    FfmpegUnavailableError,
    InvalidCutError,
    VideoTooLongError,
)

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


# ==================== 服务层单测：validate_cuts ====================


class TestValidateCuts:
    """裁剪片段规范化校验"""

    def test_single_cut_ok(self):
        """单段合法 → 返回有序列表"""
        cuts = [{"start": 1.0, "end": 8.0}]
        assert video_service.validate_cuts(cuts, "single", 10.0) == cuts

    def test_multi_cut_sorted(self):
        """多段乱序 → 按 start 升序返回"""
        cuts = [{"start": 8.0, "end": 10.0}, {"start": 2.0, "end": 4.0}]
        ordered = video_service.validate_cuts(cuts, "full", 12.0)
        assert [c["start"] for c in ordered] == [2.0, 8.0]

    def test_single_rejects_multiple(self):
        """single 模式多段 → InvalidCutError"""
        cuts = [{"start": 0.0, "end": 3.0}, {"start": 5.0, "end": 8.0}]
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts(cuts, "single", 10.0)

    def test_full_rejects_too_many(self):
        """full 模式超过 8 段 → InvalidCutError"""
        cuts = [{"start": float(i), "end": float(i) + 0.6} for i in range(9)]
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts(cuts, "full", 30.0)

    def test_overlap_rejected(self):
        """片段重叠 → InvalidCutError"""
        cuts = [
            {"start": 1.0, "end": 5.0},
            {"start": 4.0, "end": 7.0},
        ]
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts(cuts, "full", 10.0)
        # 相邻相切（start == prev_end）允许
        cuts = [
            {"start": 1.0, "end": 5.0},
            {"start": 5.0, "end": 7.0},
        ]
        assert video_service.validate_cuts(cuts, "full", 10.0)

    def test_out_of_range_rejected(self):
        """片段起点/终点越界 → InvalidCutError"""
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts([{"start": 8.0, "end": 12.0}], "single", 10.0)
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts([{"start": -1.0, "end": 3.0}], "single", 10.0)
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts([{"start": 5.0, "end": 5.0}], "single", 10.0)

    def test_segment_too_short_rejected(self):
        """单段不足 0.6s → InvalidCutError"""
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts([{"start": 1.0, "end": 1.3}], "full", 10.0)

    def test_missing_fields_rejected(self):
        """缺少 start/end → InvalidCutError"""
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts([{"start": 1.0}], "full", 10.0)

    def test_total_too_long(self):
        """拼接总长超过模式上限 → InvalidCutError（single 15s）"""
        with pytest.raises(InvalidCutError):
            video_service.validate_cuts(
                [{"start": 0.0, "end": 5.0}, {"start": 10.0, "end": 22.0}], "single", 30.0
            )


# ==================== 服务层单测：process_video 裁剪 ====================


class TestProcessVideoTrim:
    """process_video 裁剪拼接路径"""

    def test_trim_and_concat_used(self, monkeypatch, tmp_path):
        """提供 cuts → trim_and_concat 被执行，产物接续上游流程，原文件删除"""
        video_dir = tmp_path / "videos" / "1"
        video_dir.mkdir(parents=True)
        original = video_dir / "test.mp4"
        original.write_bytes(b"fake-video")

        monkeypatch.setattr(video_service.settings, "UPLOAD_DIR", str(tmp_path))
        # 裁剪后重新探测统一返回 30，仅验证流程与标志
        monkeypatch.setattr(video_service, "probe_duration", lambda p: 30.0)
        monkeypatch.setattr(video_service, "find_ffmpeg", lambda: "/usr/bin/ffmpeg")

        concat_path = str(video_dir / "test_concat.mp4")
        touched: list[str] = []
        monkeypatch.setattr(
            video_service,
            "trim_and_concat",
            lambda src, cuts, mode: touched.append(str(src)) or concat_path,
        )
        monkeypatch.setattr(video_service, "probe_frame_rate", lambda p: 30.0)
        monkeypatch.setattr(
            video_service,
            "extract_frames",
            lambda path, times, **kw: [b"\xff\xd8f" + bytes([i]) for i in range(len(times))],
        )

        cuts = [
            {"start": 2.0, "end": 6.0},
            {"start": 10.0, "end": 14.0},
        ]
        result = video_service.process_video(str(original), "full", 3.0, cuts=cuts)
        assert touched == [str(original)]
        assert result["trimmed"] is True
        assert result["segments"] == cuts
        assert result["duration"] == 30.0  # 裁剪后重新探测
        assert not os.path.isfile(original)  # 原文件已删
        assert "test_concat" in result["frame_urls"][0]  # 抽帧基于裁剪产物命名

    def test_validation_error_propagates(self, monkeypatch, tmp_path):
        """裁剪片段非法 → 抛 InvalidCutError，不触发裁剪"""
        original = tmp_path / "test.mp4"
        original.write_bytes(b"fake-video")
        monkeypatch.setattr(video_service, "probe_duration", lambda p: 10.0)
        called = {"v": False}
        monkeypatch.setattr(
            video_service,
            "trim_and_concat",
            lambda src, cuts, mode: called.__setitem__("v", True) or src,
        )
        monkeypatch.setattr(video_service, "probe_frame_rate", lambda p: 30.0)
        with pytest.raises(InvalidCutError):
            video_service.process_video(
                str(original), "single", 1.0, cuts=[{"start": 0.0, "end": 20.0}]
            )
        assert called["v"] is False

    def test_upload_over_cap_rejected(self, monkeypatch):
        """整片超过 180s → 抛 VideoTooLongError"""
        monkeypatch.setattr(video_service, "probe_duration", lambda p: 200.0)
        with pytest.raises(VideoTooLongError):
            video_service.process_video("/tmp/v.mp4", "full", None)


class TestTrimAndConcatReal:
    """trim_and_concat 真实 ffmpeg 裁切拼接（需要系统 ffmpeg）"""

    def test_two_segments_concat_duration(self, tmp_path):
        """两段裁切拼接 → 输出为单文件，时长 ≈ 两段之和"""
        ffmpeg = video_service.find_ffmpeg()
        if ffmpeg is None:
            pytest.skip("ffmpeg 未安装，跳过真实裁切拼接测试")

        src = str(tmp_path / "src.mp4")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=16:size=320x240:rate=30",
                "-pix_fmt",
                "yuv420p",
                src,
            ],
            capture_output=True,
            timeout=120,
            check=True,
        )
        cuts = [{"start": 1.0, "end": 5.0}, {"start": 8.0, "end": 12.0}]
        out = video_service.trim_and_concat(src, cuts, "full")
        assert os.path.isfile(out)
        dur = video_service.probe_duration(out)
        assert 7.4 < dur < 8.6, f"期望拼接后约 8 秒，实际 {dur:.2f}"
        os.unlink(out)


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
            video_router.video_service,
            "process_video",
            lambda path, mode, hit_time, cuts=None: fake_result,
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
            video_router.video_service, "process_video", lambda path, mode, hit_time, cuts=None: {}
        )
        files = {"file": ("img.png", b"png-bytes", "image/png")}
        response = auth_client.post("/api/video/upload", files=files, data={"mode": "single"})
        assert response.status_code == 400

    def test_upload_no_ffmpeg(self, auth_client, data_dir, monkeypatch):
        """ffmpeg 不可用 → 503"""
        from app.routers import video as video_router

        def boom(path, mode, hit_time, cuts=None):
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

    def test_upload_forwards_cuts(self, auth_client, data_dir, monkeypatch):
        """cuts JSON 透传给 process_video"""
        from app.routers import video as video_router

        captured: dict = {}

        def fake_process(path, mode, hit_time, cuts=None):
            captured["cuts"] = cuts
            return {"frames": [], "duration": 8.0}

        monkeypatch.setattr(video_router.video_service, "process_video", fake_process)
        files = {"file": ("swing.mp4", b"fake", "video/mp4")}
        data = {"mode": "full", "cuts": '[{"start":1.0,"end":4.0},{"start":6.0,"end":9.0}]'}
        response = auth_client.post("/api/video/upload", files=files, data=data)
        assert response.status_code == 200
        assert captured["cuts"] == [{"start": 1.0, "end": 4.0}, {"start": 6.0, "end": 9.0}]

    def test_upload_no_cuts_passes_none(self, auth_client, data_dir, monkeypatch):
        """不传 cuts → process_video 收到 None"""
        from app.routers import video as video_router

        captured: dict = {}

        def fake_process(path, mode, hit_time, cuts=None):
            captured["cuts"] = cuts
            return {"frames": [], "duration": 8.0}

        monkeypatch.setattr(video_router.video_service, "process_video", fake_process)
        files = {"file": ("swing.mp4", b"fake", "video/mp4")}
        response = auth_client.post("/api/video/upload", files=files, data={"mode": "single"})
        assert response.status_code == 200
        assert captured["cuts"] is None

    def test_upload_invalid_cuts_json(self, auth_client, data_dir, monkeypatch):
        """cuts 非合法 JSON → 400"""
        files = {"file": ("swing.mp4", b"fake", "video/mp4")}
        data = {"mode": "full", "cuts": "not-json"}
        response = auth_client.post("/api/video/upload", files=files, data=data)
        assert response.status_code == 400

    def test_upload_invalid_cut_rejected(self, auth_client, data_dir, monkeypatch):
        """裁剪片段校验失败 → 400 + 明确提示"""
        from app.routers import video as video_router

        def boom(path, mode, hit_time, cuts=None):
            raise InvalidCutError("片段存在重叠，请调整")

        monkeypatch.setattr(video_router.video_service, "process_video", boom)
        files = {"file": ("swing.mp4", b"fake", "video/mp4")}
        data = {"mode": "full", "cuts": '[{"start":1.0,"end":5.0},{"start":4.0,"end":7.0}]'}
        response = auth_client.post("/api/video/upload", files=files, data=data)
        assert response.status_code == 400
        assert "重叠" in response.json()["message"]
