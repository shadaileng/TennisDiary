"""POST /api/pose/analyze MediaPipe 姿态推理接口测试

mediapipe 为重型依赖，测试环境不实际安装/推理，全部用 monkeypatch 隔离；
measure_angles / 关键点测量为纯函数，直接断言。
"""

from typing import ClassVar

import pytest

from app.services import pose_service

# ==================== 关键点构造辅助 ====================


def make_landmarks(
    vis: float = 0.9, overrides: dict[int, tuple[float, float]] | None = None
) -> list[dict]:
    """构造 33 关键点列表（默认全身可见），overrides 形如 {14: (0.5, 0.4), ...}"""
    lms: list[dict] = []
    for i in range(33):
        lms.append({"x": 0.5, "y": 0.3 + i * 0.01, "z": 0.0, "visibility": vis})
    for idx, (x, y) in (overrides or {}).items():
        lms[idx]["x"] = x
        lms[idx]["y"] = y
    return lms


# ==================== 服务层单测：measure_angles ====================


class TestMeasureAngles:
    """pose_service.measure_angles 角度测量（与 pose.ts 一致）"""

    def test_elbow_right_angle(self):
        """肩(12)-肘(14)-腕(16) 构成 90° → 肘角 ≈ 90"""
        lms = make_landmarks(
            overrides={12: (0.5, 0.2), 14: (0.5, 0.4), 16: (0.7, 0.4)},  # 右肩/右肘/右腕
        )
        m = pose_service.measure_angles(lms)
        assert m is not None
        assert m["elbowAngle"] == pytest.approx(90.0, abs=1.0)

    def test_knee_straight(self):
        """髋(24)-膝(26)-踝(28) 竖直 → 膝角 ≈ 180"""
        lms = make_landmarks(
            overrides={24: (0.5, 0.5), 26: (0.5, 0.7), 28: (0.5, 0.9)},  # 右髋/右膝/右踝
        )
        m = pose_service.measure_angles(lms)
        assert m is not None
        assert m["kneeAngle"] == pytest.approx(180.0, abs=1.0)

    def test_trunk_lean_nonzero(self):
        """肩中点相对髋中点横向偏移 → 躯干倾角非零"""
        lms = make_landmarks(
            overrides={11: (0.55, 0.3), 12: (0.55, 0.3), 23: (0.45, 0.6), 24: (0.45, 0.6)},
        )
        m = pose_service.measure_angles(lms)
        assert m is not None
        assert m["trunkLean"] != pytest.approx(0.0, abs=0.01)

    def test_visibility_insufficient(self):
        """肘部关键点 visibility < 0.4 → 跳过测量（返回 None）"""
        lms = make_landmarks(overrides={14: (0.5, 0.4)})
        lms[14]["visibility"] = 0.2
        assert pose_service.measure_angles(lms) is None

    def test_short_landmarks(self):
        """关键点数量不足 → None"""
        assert pose_service.measure_angles([]) is None


# ==================== 服务层单测：analyze_frames ====================


class TestAnalyzeFrames:
    """pose_service.analyze_frames 逐帧推理编排"""

    FAKE_LMS: ClassVar = [{"x": 0.5, "y": 0.3, "z": 0.0, "visibility": 0.9} for _ in range(33)]

    def test_normal(self, monkeypatch):
        """全部帧检测成功 → frames + metrics + detected=true"""
        monkeypatch.setattr(
            pose_service, "detect_pose", lambda img: [dict(lm) for lm in self.FAKE_LMS]
        )
        result = pose_service.analyze_frames(
            ["data:image/jpeg;base64,AAAA", "data:image/jpeg;base64,BBBB"]
        )
        assert result["detected"] is True
        assert len(result["frames"]) == 2
        assert len(result["frames"][0]["landmarks"]) == 33
        assert result["metrics"] is not None
        assert {"elbowAngle", "kneeAngle", "trunkLean"} <= set(result["metrics"].keys())

    def test_no_detection(self, monkeypatch):
        """所有帧无人检测 → detected=false + metrics=None"""
        monkeypatch.setattr(pose_service, "detect_pose", lambda img: None)
        result = pose_service.analyze_frames(["data:image/jpeg;base64,AAAA"])
        assert result["detected"] is False
        assert result["metrics"] is None
        assert result["frames"][0]["landmarks"] == []

    def test_invalid_base64(self, monkeypatch):
        """帧 base64 非法 → 抛 ValueError"""
        monkeypatch.setattr(pose_service, "detect_pose", lambda img: self.FAKE_LMS)
        with pytest.raises(ValueError):
            pose_service.analyze_frames(["@@@not-base64@@@"])

    def test_first_detectable_frame_metrics(self, monkeypatch):
        """首帧无人、次帧有人 → metrics 取次帧"""
        calls: list[int] = []

        def fake_detect(img):
            calls.append(1)
            return [dict(lm) for lm in self.FAKE_LMS] if len(calls) == 2 else None

        monkeypatch.setattr(pose_service, "detect_pose", fake_detect)
        frames = ["data:image/jpeg;base64,AAAA", "data:image/jpeg;base64,BBBB"]
        result = pose_service.analyze_frames(frames)
        assert result["detected"] is True
        assert result["frames"][0]["landmarks"] == []
        assert len(result["frames"][1]["landmarks"]) == 33
        assert result["metrics"] is not None


# ==================== 服务层单测：mediapipe API 兼容 ====================


class TestMediapipeCompat:
    """真实推理路径的 mediapipe API 兼容性
    （mediapipe 1.x 无 vision.BaseOptions / tasks.python.core.image）"""

    def test_api_paths_exist(self):
        if not pose_service.mediapipe_available():
            pytest.skip("mediapipe 未安装")
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python

        assert hasattr(mp, "Image")
        assert hasattr(mp, "ImageFormat")
        assert hasattr(mp_python, "BaseOptions")
        assert hasattr(mp_python, "vision")


# ==================== 服务层单测：find_model ====================


class TestFindModel:
    def test_model_exists(self, monkeypatch, tmp_path):
        """模型文件存在 → 返回路径"""
        model = tmp_path / "pose.task"
        model.write_bytes(b"fake")
        monkeypatch.setattr(pose_service.settings, "POSE_MODEL_PATH", str(model))
        assert pose_service.find_model() == str(model)

    def test_model_missing(self, monkeypatch, tmp_path):
        """模型文件不存在 → None"""
        monkeypatch.setattr(
            pose_service.settings, "POSE_MODEL_PATH", str(tmp_path / "missing.task")
        )
        assert pose_service.find_model() is None


# ==================== 服务层单测：draw_skeleton（骨架绘制） ====================


def _fake_jpeg(width: int = 64, height: int = 64) -> bytes:
    """生成一张纯色 JPEG"""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (120, 120, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def _throw(exc: Exception) -> None:
    """lambda 内抛异常（保持行宽）"""
    raise exc


class TestDrawSkeleton:
    """pose_service.draw_skeleton 骨架绘制"""

    def test_returns_jpeg(self):
        """正常关键点 → 返回合法 JPEG（以 FF D8 FF 开头）"""
        out = pose_service.draw_skeleton(_fake_jpeg(), make_landmarks())
        assert out[:3] == b"\xff\xd8\xff"

    def test_low_visibility_filtered(self):
        """全部关键点 visibility<0.4 → 跳过绘制，仍返回合法 JPEG（不崩溃）"""
        lms = make_landmarks(vis=0.1)
        out = pose_service.draw_skeleton(_fake_jpeg(), lms)
        assert out[:3] == b"\xff\xd8\xff"

    def test_different_size_keeps_dimensions(self):
        """骨架帧与原帧尺寸一致"""
        from PIL import Image

        out = pose_service.draw_skeleton(_fake_jpeg(80, 50), make_landmarks())
        img = Image.open(__import__("io").BytesIO(out))
        assert img.size == (80, 50)

    def test_invalid_image_raises(self):
        """非图片 bytes → ValueError"""
        with pytest.raises(ValueError):
            pose_service.draw_skeleton(b"not-an-image", make_landmarks())


# ==================== 服务层单测：analyze_frames + save_skeleton ====================


class TestAnalyzeFramesSaveSkeleton:
    """analyze_frames 的 save_skeleton / video_url 路径（骨架帧落盘 + 视频编码）"""

    def _fake_frame(self) -> str:
        """真实 JPEG 的 base64 dataURL"""
        import base64

        return "data:image/jpeg;base64," + base64.b64encode(_fake_jpeg()).decode()

    def _setup_video(self, data_dir, uid=1, name="abc.mp4"):
        """在隔离 UPLOAD_DIR 下构造 videos/{uid}/{name}，返回绝对路径"""
        video_dir = data_dir / "uploads" / "videos" / str(uid)
        video_dir.mkdir(parents=True, exist_ok=True)
        video_path = video_dir / name
        video_path.write_bytes(b"fake-video")
        return video_path

    def test_save_skeleton_writes_files_and_urls(self, monkeypatch, data_dir):
        """检出帧 → 骨架帧落盘 + skeleton_frames/video_url/thumb"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: TestAnalyzeFrames.FAKE_LMS)

        def fake_encode(paths, out, fps):
            with open(out, "wb") as f:
                f.write(b"mp4")
            return True

        monkeypatch.setattr(ps, "encode_skeleton_video", fake_encode)
        self._setup_video(data_dir)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))

        result = ps.analyze_frames(
            [self._fake_frame(), self._fake_frame()],
            video_url="videos/1/abc.mp4",
            save_skeleton=True,
            duration=10.0,
        )
        assert result["skeleton_frames"] == [
            "videos/1/abc_sk0.jpg",
            "videos/1/abc_sk1.jpg",
        ]
        assert result["skeleton_video_url"] == "videos/1/abc_skeleton.mp4"
        assert result["skeleton_thumb"] == "videos/1/abc_sk0.jpg"
        assert (data_dir / "uploads" / "videos" / "1" / "abc_sk0.jpg").is_file()
        assert (data_dir / "uploads" / "videos" / "1" / "abc_sk1.jpg").is_file()

    def test_save_skeleton_without_ffmpeg(self, monkeypatch, data_dir):
        """ffmpeg 不可用 → 仅保留骨架帧，skeleton_video_url 为 None"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: TestAnalyzeFrames.FAKE_LMS)
        monkeypatch.setattr(ps, "find_ffmpeg", lambda: None)
        self._setup_video(data_dir)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))

        result = ps.analyze_frames(
            [self._fake_frame(), self._fake_frame()],
            video_url="videos/1/abc.mp4",
            save_skeleton=True,
        )
        assert result["skeleton_video_url"] is None
        assert len(result["skeleton_frames"]) == 2

    def test_save_skeleton_requires_video_url(self, monkeypatch):
        """save_skeleton=True 但无 video_url → 不产出骨架字段（不崩溃）"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: TestAnalyzeFrames.FAKE_LMS)
        result = ps.analyze_frames([self._fake_frame()], save_skeleton=True)
        assert result["skeleton_frames"] == []
        assert result["skeleton_video_url"] is None
        assert result["skeleton_thumb"] is None

    def test_video_url_traversal(self, monkeypatch, data_dir):
        """video_url 越界 → ValueError"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: TestAnalyzeFrames.FAKE_LMS)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        with pytest.raises(ValueError):
            ps.analyze_frames(
                [self._fake_frame()],
                video_url="../evil.mp4",
                save_skeleton=True,
            )

    def test_video_url_missing_file(self, monkeypatch, data_dir):
        """video_url 指向不存在的视频 → ValueError"""
        from app.services import pose_service as ps

        monkeypatch.setattr(ps, "detect_pose", lambda img: TestAnalyzeFrames.FAKE_LMS)
        monkeypatch.setattr(ps.settings, "UPLOAD_DIR", str(data_dir / "uploads"))
        with pytest.raises(ValueError):
            ps.analyze_frames(
                [self._fake_frame()],
                video_url="videos/1/not-exist.mp4",
                save_skeleton=True,
            )


# ==================== 接口测试：POST /api/pose/analyze ====================


class TestPoseAnalyze:
    """测试 /api/pose/analyze"""

    VALID_PAYLOAD: ClassVar[dict] = {"frames": ["data:image/jpeg;base64,/9j/4AAQSkZJRg=="]}

    FAKE_RESULT: ClassVar[dict] = {
        "frames": [
            {"landmarks": [{"x": 0.5, "y": 0.3, "z": 0.0, "visibility": 0.9} for _ in range(33)]}
        ],
        "metrics": {"elbowAngle": 95.2, "kneeAngle": 140.1, "trunkLean": 8.3},
        "detected": True,
    }

    def test_analyze_success(self, auth_client, monkeypatch):
        """推理成功 → 200 + landmarks 33 项 + metrics"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)
        monkeypatch.setattr(
            pose_router.pose_service,
            "analyze_frames",
            lambda frames, video_url=None, save_skeleton=False, duration=None: self.FAKE_RESULT,
        )
        response = auth_client.post("/api/pose/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["detected"] is True
        assert len(data["frames"][0]["landmarks"]) == 33
        assert data["metrics"]["elbowAngle"] == 95.2

    def test_analyze_no_detection(self, auth_client, monkeypatch):
        """无人检测 → 200 + detected=false + metrics=null（不报错）"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)
        monkeypatch.setattr(
            pose_router.pose_service,
            "analyze_frames",
            lambda frames, video_url=None, save_skeleton=False, duration=None: {
                "frames": [{"landmarks": []}],
                "metrics": None,
                "detected": False,
            },
        )
        response = auth_client.post("/api/pose/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["detected"] is False
        assert data["metrics"] is None

    def test_analyze_model_missing(self, auth_client, monkeypatch):
        """模型缺失 / mediapipe 未安装 → 503"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: False)
        response = auth_client.post("/api/pose/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 503

    def test_analyze_service_error(self, auth_client, monkeypatch):
        """推理服务异常 → 503"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)

        def boom(frames, video_url=None, save_skeleton=False, duration=None):
            raise pose_service.PoseUnavailableError("模型加载失败")

        monkeypatch.setattr(pose_router.pose_service, "analyze_frames", boom)
        response = auth_client.post("/api/pose/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 503

    def test_analyze_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.post("/api/pose/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code in (401, 403)

    def test_analyze_empty_frames(self, auth_client, monkeypatch):
        """空 frames → 422 参数校验失败"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)
        response = auth_client.post("/api/pose/analyze", json={"frames": []})
        assert response.status_code == 422

    def test_analyze_save_skeleton(self, auth_client, monkeypatch):
        """save_skeleton + video_url → 200 + 骨架三字段透传"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)
        fake = {
            **self.FAKE_RESULT,
            "skeleton_frames": ["videos/1/abc_sk0.jpg"],
            "skeleton_video_url": "videos/1/abc_skeleton.mp4",
            "skeleton_thumb": "videos/1/abc_sk0.jpg",
        }

        def fake_analyze(frames, video_url=None, save_skeleton=False, duration=None):
            assert video_url == "videos/1/abc.mp4"
            assert save_skeleton is True
            return fake

        monkeypatch.setattr(pose_router.pose_service, "analyze_frames", fake_analyze)
        payload = {
            **self.VALID_PAYLOAD,
            "video_url": "videos/1/abc.mp4",
            "save_skeleton": True,
            "duration": 12.0,
        }
        response = auth_client.post("/api/pose/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["skeleton_video_url"] == "videos/1/abc_skeleton.mp4"
        assert data["skeleton_frames"] == ["videos/1/abc_sk0.jpg"]

    def test_analyze_video_url_traversal_400(self, auth_client, monkeypatch):
        """video_url 越界 → 服务层抛 ValueError → 400"""
        from app.routers import pose as pose_router

        monkeypatch.setattr(pose_router.pose_service, "is_available", lambda: True)
        monkeypatch.setattr(
            pose_router.pose_service,
            "analyze_frames",
            lambda frames, video_url=None, save_skeleton=False, duration=None: _throw(
                ValueError("video_url 非法或不存在")
            ),
        )
        payload = {**self.VALID_PAYLOAD, "video_url": "../evil.mp4", "save_skeleton": True}
        response = auth_client.post("/api/pose/analyze", json=payload)
        assert response.status_code == 400
