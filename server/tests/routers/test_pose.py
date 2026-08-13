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
            pose_router.pose_service, "analyze_frames", lambda frames: self.FAKE_RESULT
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
            lambda frames: {"frames": [{"landmarks": []}], "metrics": None, "detected": False},
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

        def boom(frames):
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
