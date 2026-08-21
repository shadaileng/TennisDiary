"""正手动作分析全链路调试测试（真实视频端到端，非 CI 常规用例）

覆盖链路：视频抽帧（process_video）→ 姿态推理（analyze_frames）→ AI 六维评分（analyze_swing）。

调试定位：设备上传报「无法解析视频时长」的对照——同一素材在本地能跑通即佐证
问题出在设备→服务端的字节传输/文件本身，而非服务端或 ffprobe 解析。

- 素材：env `TENNIS_DEBUG_VIDEO`，默认 `docs/reference/VID_20260816_160443.mp4`
- 前置：ffmpeg（probe/抽帧）；mediapipe + 姿态模型（缺失时跳过姿态用例）
- AI：读生效配置（DB > env）；缺 Key 或调用失败时校验本地降级结果
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import logger
from app.services import ai_service, pose_service, video_service
from app.services.config_service import AIConfig, get_ai_config

DEBUG_VIDEO = Path(
    os.environ.get(
        "TENNIS_DEBUG_VIDEO",
        Path(__file__).resolve().parents[2] / "docs/reference/VID_20260816_160443.mp4",
    )
)

HAS_POSE = pose_service.mediapipe_available() and pose_service.find_model() is not None


def _effective_ai_config():
    """生效 AI 配置：env 显式覆盖（TENNIS_DEBUG_AI_*）> DB（get_ai_config，与服务端一致）"""
    if os.environ.get("TENNIS_DEBUG_AI_KEY"):
        return AIConfig(
            api_key=os.environ["TENNIS_DEBUG_AI_KEY"],
            base_url=os.environ.get(
                "TENNIS_DEBUG_AI_BASE_URL", "https://api.agnes-ai.cn/v1"
            ).rstrip("/"),
            model=os.environ.get("TENNIS_DEBUG_AI_MODEL", "agnes-2.5-flash"),
            provider="env 覆盖",
        )
    with SessionLocal() as db:
        return get_ai_config(db)


@pytest.fixture(scope="module")
def pipeline():
    """在临时目录复制真实素材 → 跑通 抽帧 + 姿态，返回 {video, pose}"""
    with tempfile.TemporaryDirectory(prefix="debug_fh_", dir=settings.UPLOAD_DIR) as tmp:
        working = Path(tmp) / "debug_input.mp4"
        shutil.copy2(DEBUG_VIDEO, working)
        vres = video_service.process_video(str(working), mode="single", hit_time=None)
    pres = pose_service.analyze_frames(
        vres["frames"],
        duration=vres["duration"],
        frame_rate=vres["frame_rate"],
    )
    return {"video": vres, "pose": pres}


def test_forehand_video_processed(pipeline):
    vres = pipeline["video"]
    logger.info(f"video.duration={vres['duration']} fps={vres['frame_rate']} mode={vres['mode']}")
    assert vres["mode"] == "single"
    assert 120 <= vres["duration"] <= 125  # 实测 121.490489s，非恰为 0/非整
    assert vres["frame_rate"] > 0
    assert len(vres["frames"]) == 7  # single 模式 7 个采样帧
    assert len(vres["frame_urls"]) == 7
    assert vres["thumbnail"].startswith("data:")


@pytest.mark.skipif(not HAS_POSE, reason="mediapipe 或姿态模型不可用")
def test_forehand_pose_inference(pipeline):
    pres = pipeline["pose"]
    assert len(pres["frames"]) == len(pipeline["video"]["frames"])
    assert "detected" in pres
    assert "metrics" in pres

    if pres["detected"]:
        logger.info(f"姿态检测成功: {pres['metrics']}")
    else:
        logger.warning("未检测到人 → 检查视频是否含清晰单人")


def test_forehand_ai_report(pipeline):
    ai_config = _effective_ai_config()
    frames = pipeline["video"]["frames"]

    if not ai_config.api_key:
        report = ai_service.build_local_report("正手", pipeline["pose"]["metrics"])
        mode = "local(无 Key)"
    else:
        try:
            report = asyncio.run(ai_service.analyze_swing(frames, "正手", "single", ai_config))
            mode = f"ai({ai_config.provider})"
        except Exception as exc:  # noqa: BLE001 - 调试测试需捕获失败并落降级
            logger.warning(f"AI 调用失败，落本地降级: {exc}")
            report = ai_service.build_local_report("正手", pipeline["pose"]["metrics"])
            mode = "degraded"

    dims = report.get("dimensions") or []
    if mode.startswith("ai"):
        assert len(dims) == len(ai_service.DIMENSIONS)  # AI 路径六维齐全
    assert report.get("strengths") is not None
    assert report.get("improvements")
    logger.info(f"正手分析完成({mode}): score={report.get('score')} dims={len(dims)}")
