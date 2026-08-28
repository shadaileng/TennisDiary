"""文件 MIME 类型探测（确定性映射 + ffprobe/PIL 真实探测）

问题背景：
- 上传时客户端（小程序 uni.uploadFile）常不带 Content-Type，后端落库的 mime_type 可能为空。
- 预览端点若用 mimetypes.guess_type 兜底，结果依赖运行环境的 mime.types，
  线上 slim 镜像可能把 .mp4 解析成 audio/mp4，导致前端 <audio> 渲染 mp4（被当音频）。
- 本模块提供确定性扩展名映射，并优先用 ffprobe（音视频）/PIL（图片）探测真实类型，
  保证 .mp4 永远映射为 video/mp4，与运行时环境无关。
"""

import os
import shutil
import subprocess

from app.core.logging import get_logger

log = get_logger("mime")

# 确定性扩展名 -> MIME 映射（不依赖运行时 mimetypes）
EXTENSION_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/mp4",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".pdf": "application/pdf",
}

# 容器格式名（ffprobe format_name，逗号分隔）-> MIME 子类型映射
_FORMAT_MIME: dict[str, str] = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "m4v": "video/mp4",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "matroska": "video/x-matroska",
    "webm": "video/webm",
    "flv": "video/x-flv",
}

# 图片真实格式（PIL Image.format）-> MIME
_PIL_FORMAT_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
}


def find_ffprobe() -> str | None:
    """定位 ffprobe：优先系统 PATH，回退 imageio-ffmpeg 自带二进制"""
    sys_bin = shutil.which("ffprobe")
    if sys_bin:
        return sys_bin
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffprobe_exe()
    except (ImportError, AttributeError, RuntimeError, OSError) as exc:
        log.debug("imageio_ffmpeg 探测失败: %s", exc)
        return None


def _ext_mime(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    return EXTENSION_MIME.get(ext)


def detect_image_mime(path: str) -> str:
    """图片 MIME：优先用 PIL 读取真实格式，回退扩展名映射，再回退 octet-stream"""
    try:
        from PIL import Image

        with Image.open(path) as img:
            fmt = img.format
            if fmt and fmt in _PIL_FORMAT_MIME:
                return _PIL_FORMAT_MIME[fmt]
    except Exception as exc:  # noqa: BLE001  # PIL 可能抛出多种异常，统一回退扩展名
        log.debug("PIL 读取图片格式失败，回退扩展名: path=%s error=%s", path, exc)

    return _ext_mime(path) or "application/octet-stream"


def detect_media_mime(path: str) -> str:
    """音视频 MIME：优先 ffprobe 探测真实流类型与容器，回退扩展名映射

    返回 video/* / audio/* 之一；ffprobe 缺失或失败时安全回退，不抛错。
    """
    ffprobe = find_ffprobe()
    if ffprobe and os.path.isfile(path):
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type:format=format_name",
                    "-of",
                    "json",
                    path,
                ],
                capture_output=True,
                timeout=30,
            )
            if proc.returncode == 0:
                return _parse_ffprobe(proc.stdout.decode("utf-8", "replace"), path)
        except (subprocess.SubprocessError, OSError) as exc:
            log.warning("ffprobe 探测失败，回退扩展名: path=%s error=%s", path, exc)

    return _ext_mime(path) or "application/octet-stream"


def _parse_ffprobe(stdout: str, path: str) -> str:
    """从 ffprobe json 输出推断 MIME：含 video 流 -> video/*，仅 audio -> audio/*

    优先用文件扩展名对应的标准 MIME（如 .mp4 -> video/mp4，即使 ffprobe
    把容器格式报成 mov），保证与扩展名语义一致；无扩展名时再按容器格式名推断。
    """
    import json

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        log.debug("ffprobe 输出解析失败: %s", exc)
        return _ext_mime(path) or "application/octet-stream"

    streams = data.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    format_name = ""
    fmt = data.get("format", {})
    if isinstance(fmt, dict):
        format_name = (fmt.get("format_name") or "").lower()

    # 取第一个已知的容器格式名
    container_subtype = None
    for name in format_name.split(","):
        name = name.strip()
        if name in _FORMAT_MIME:
            container_subtype = _FORMAT_MIME[name]
            break

    ext_mime = _ext_mime(path)
    if has_video:
        # 有视频流：优先扩展名对应的 video/*（.mp4 -> video/mp4），否则用容器类型
        if ext_mime and ext_mime.startswith("video/"):
            return ext_mime
        return container_subtype or "video/mp4"
    if has_audio:
        # 仅有音频流：优先扩展名对应的 audio/*（.m4a -> audio/mp4），否则 audio 容器
        if ext_mime and ext_mime.startswith("audio/"):
            return ext_mime
        if container_subtype and container_subtype.startswith("audio/"):
            return container_subtype
        return "audio/mp4"
    # 无流信息：退而用容器格式名推断
    if container_subtype:
        return container_subtype
    return ext_mime or "application/octet-stream"


_IMAGE_SOURCES = {"avatar", "gear_image", "image", "other_image"}
_MEDIA_SOURCES = {"video", "video_frame", "audio"}


def detect_mime_type(path: str, upload_source: str = "") -> str:
    """入口：根据来源选择图片/音视频探测，统一回退到扩展名映射

    - 图片类来源 -> detect_image_mime
    - 音视频类来源 -> detect_media_mime
    - 未知/兜底 -> 扩展名映射
    """
    source = (upload_source or "").lower()
    if source in _IMAGE_SOURCES:
        return detect_image_mime(path)
    if source in _MEDIA_SOURCES:
        return detect_media_mime(path)
    # 未知来源：按扩展名粗判，音视频扩展名走媒体探测，否则图片探测
    ext = os.path.splitext(path)[1].lower()
    if ext in (".mp4", ".mov", ".m4v", ".m4a", ".mp3", ".wav", ".webm", ".flv", ".matroska"):
        return detect_media_mime(path)
    if ext in EXTENSION_MIME and EXTENSION_MIME[ext].startswith("image/"):
        return detect_image_mime(path)
    return _ext_mime(path) or "application/octet-stream"
