"""MIME 探测工具测试（Step 116）

覆盖：确定性扩展名映射、图片 PIL 探测、音视频 ffprobe 探测、兜底逻辑。
标记为 fast：纯函数，不依赖 DB/TestClient。
"""

import os

import pytest

from app.core import mime as mime_module
from app.core.mime import (
    EXTENSION_MIME,
    detect_image_mime,
    detect_media_mime,
    detect_mime_type,
)

pytestmark = pytest.mark.fast


def _make_tmp_mp4(tmp_path: str, with_video: bool = True) -> str:
    """用 ffmpeg 生成一个极小的测试 mp4（可选仅音频）"""
    import subprocess

    path = os.path.join(tmp_path, "sample.mp4")
    if with_video:
        # 生成 0.2s 带测试图卡的视频
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=64x64:d=0.2",
                "-pix_fmt",
                "yuv420p",
                path,
            ],
            capture_output=True,
            timeout=30,
        )
    else:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=0.2",
                "-c:a",
                "aac",
                path,
            ],
            capture_output=True,
            timeout=30,
        )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert os.path.isfile(path)
    return path


def test_extension_mime_mp4_is_video_not_audio():
    """核心回归：.mp4 必须映射为 video/mp4，绝不能 audio/mp4"""
    assert EXTENSION_MIME[".mp4"] == "video/mp4"
    assert EXTENSION_MIME[".mp4"] != "audio/mp4"


def test_extension_mime_known_types():
    assert EXTENSION_MIME[".jpg"] == "image/jpeg"
    assert EXTENSION_MIME[".png"] == "image/png"
    assert EXTENSION_MIME[".mov"] == "video/quicktime"
    assert EXTENSION_MIME[".m4a"] == "audio/mp4"
    assert EXTENSION_MIME[".mp3"] == "audio/mpeg"
    assert EXTENSION_MIME[".pdf"] == "application/pdf"


def test_detect_media_mime_mp4(tmp_path):
    """ffprobe 能识别真实 mp4 为 video/mp4"""
    path = _make_tmp_mp4(str(tmp_path), with_video=True)
    assert detect_media_mime(path) == "video/mp4"


def test_detect_media_mime_audio_only(tmp_path):
    """纯音频 mp4 应识别为 audio/mp4"""
    path = _make_tmp_mp4(str(tmp_path), with_video=False)
    assert detect_media_mime(path) == "audio/mp4"


def test_detect_media_mime_fallback_when_ffprobe_missing(tmp_path, monkeypatch):
    """ffprobe 不可用时安全回退扩展名映射"""
    monkeypatch.setattr(mime_module, "find_ffprobe", lambda: None)
    path = os.path.join(str(tmp_path), "x.mp4")
    with open(path, "wb") as f:
        f.write(b"\x00\x01\x02")
    assert detect_media_mime(path) == "video/mp4"


def test_detect_image_mime_pil(tmp_path):
    """PIL 读取真实图片格式返回正确 MIME"""
    from PIL import Image

    path = os.path.join(str(tmp_path), "img.png")
    Image.new("RGB", (8, 8), color="red").save(path, format="PNG")
    assert detect_image_mime(path) == "image/png"


def test_detect_image_mime_fake_extension(tmp_path):
    """伪扩展名（.jpg 实为 png）应被 PIL 纠正为 image/png"""
    from PIL import Image

    path = os.path.join(str(tmp_path), "fake.jpg")
    Image.new("RGB", (8, 8), color="green").save(path, format="PNG")
    assert detect_image_mime(path) == "image/png"


def test_detect_mime_type_dispatches_by_source(tmp_path):
    """来源决定走图片/音视频探测"""
    video = _make_tmp_mp4(str(tmp_path), with_video=True)
    from PIL import Image

    img_path = os.path.join(str(tmp_path), "a.png")
    Image.new("RGB", (8, 8)).save(img_path, format="PNG")

    assert detect_mime_type(video, "video") == "video/mp4"
    assert detect_mime_type(img_path, "avatar") == "image/png"
    # 未知来源按扩展名粗判
    assert detect_mime_type(video) == "video/mp4"
