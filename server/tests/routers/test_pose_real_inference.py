"""真实推理路径测试（不 monkeypatch mediapipe）

验证 mp_image_from_bytes / detect_pose / measure_angles 链路在真实数据上可用。
"""

import base64
from pathlib import Path

import pytest

from app.services import pose_service

# 测试视频帧路径
_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_TEST_FRAME = _FIXTURES_DIR / "test_frame0.jpg"


def _load_frame_as_base64() -> str:
    """加载测试帧为 base64 dataURL"""
    if not _TEST_FRAME.exists():
        pytest.skip(f"测试帧不存在: {_TEST_FRAME}")
    with open(_TEST_FRAME, "rb") as f:
        img_bytes = f.read()
    return f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"


class TestRealInference:
    """真实推理路径：不 monkeypatch mediapipe，直接调用 analyze_frames"""

    @pytest.mark.skipif(
        not pose_service.mediapipe_available(),
        reason="mediapipe 未安装",
    )
    @pytest.mark.skipif(
        not pose_service.find_model(),
        reason="姿态模型缺失",
    )
    def test_analyze_frames_with_real_image(self):
        """用真实 JPEG 帧调用 analyze_frames → 正常返回，不抛异常"""
        frame = _load_frame_as_base64()
        result = pose_service.analyze_frames([frame])
        assert "frames" in result
        assert len(result["frames"]) == 1
        # 可能无人检测（测试帧是静态图，不一定有人）
        assert "detected" in result
        assert "metrics" in result

    @pytest.mark.skipif(
        not pose_service.mediapipe_available(),
        reason="mediapipe 未安装",
    )
    @pytest.mark.skipif(
        not pose_service.find_model(),
        reason="姿态模型缺失",
    )
    def test_mp_image_from_bytes_with_real_jpeg(self):
        """mp_image_from_bytes 能处理真实 JPEG"""
        frame = _load_frame_as_base64()
        # 内部调用 detect_pose → mp_image_from_bytes
        # 如果不抛异常即通过
        image_bytes = pose_service._decode_frame(frame)
        from mediapipe import Image as MpImage
        mp_img = pose_service.mp_image_from_bytes(image_bytes, MpImage)
        assert mp_img is not None

    @pytest.mark.skipif(
        not pose_service.mediapipe_available(),
        reason="mediapipe 未安装",
    )
    def test_landmarker_loads_once(self):
        """_get_landmarker 懒加载成功 → 不抛异常"""
        lm = pose_service._get_landmarker()
        assert lm is not None

    @pytest.mark.skipif(
        not pose_service.mediapipe_available(),
        reason="mediapipe 未安装",
    )
    @pytest.mark.skipif(
        not pose_service.find_model(),
        reason="姿态模型缺失",
    )
    def test_detect_pose_with_real_image(self):
        """detect_pose 能处理真实 JPEG（可能返回 None 表示无人）"""
        frame = _load_frame_as_base64()
        image_bytes = pose_service._decode_frame(frame)
        result = pose_service.detect_pose(image_bytes)
        # result 可能是 None（无人）或 landmarks 列表
        assert result is None or isinstance(result, list)
