"""视频上传与 ffmpeg 抽帧服务层

参考 Web 版 CoachAnalyze.tsx 的采样时间点与帧规格：
- single：7 帧，偏移 [-0.6, -0.35, -0.15, 0, 0.2, 0.5, 0.9]（相对击球瞬间）
- full：8 帧，全片均匀 (i+0.5)/8
- 帧规格：640px 宽 JPEG，质量 0.72
"""

import os
import re
import shutil
import subprocess

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("user")

# single 采样偏移（秒，相对 hit_time）
_SINGLE_OFFSETS = [-0.6, -0.35, -0.15, 0, 0.2, 0.5, 0.9]
_FULL_FRAME_COUNT = 8
_FRAME_WIDTH = 640
_FRAME_QUALITY = 2  # ffmpeg q:v 2 ≈ JPEG 质量 0.72

# 时长限制（秒）
_MAX_DURATION = {"single": 15.0, "full": 90.0}


class FfmpegUnavailableError(RuntimeError):
    """ffmpeg 二进制不可用"""


class VideoTooLongError(ValueError):
    """视频时长超过模式限制"""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


def find_ffmpeg() -> str | None:
    """优先系统 ffmpeg，回退 imageio-ffmpeg 自带二进制"""
    sys_bin = shutil.which("ffmpeg")
    if sys_bin:
        return sys_bin
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def _parse_duration_from_ffmpeg_stderr(stderr: str) -> float:
    """从 ffmpeg -i stderr 解析 Duration: HH:MM:SS.xx"""
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
    if not match:
        raise ValueError("无法解析视频时长")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def probe_duration(path: str) -> float:
    """探测视频时长：优先 ffprobe，回退 ffmpeg stderr 解析"""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                path,
            ],
            capture_output=True,
            timeout=30,
        )
        if proc.returncode == 0:
            try:
                return float(proc.stdout.decode().strip())
            except ValueError:
                pass
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        proc = subprocess.run([ffmpeg, "-i", path], capture_output=True, timeout=30)
        return _parse_duration_from_ffmpeg_stderr(proc.stderr.decode(errors="replace"))
    raise FfmpegUnavailableError("ffmpeg 不可用")


def probe_frame_rate(path: str) -> float:
    """探测视频帧率：优先 ffprobe，回退默认 30fps

    返回浮点数帧率（如 29.97, 30.0, 60.0）
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=r_frame_rate,avg_frame_rate",
                "-of",
                "default=nw=1:nk=1",
                path,
            ],
            capture_output=True,
            timeout=30,
        )
        if proc.returncode == 0:
            frame_rate_str = proc.stdout.decode().strip()
            if frame_rate_str:
                try:
                    # 处理分数格式如 "30000/1001"
                    if "/" in frame_rate_str:
                        num, den = frame_rate_str.split("/")
                        return float(num) / float(den)
                    return float(frame_rate_str)
                except (ValueError, ZeroDivisionError):
                    pass
    return 30.0  # 默认帧率


def build_sampling_times(mode: str, duration: float, hit_time: float | None) -> list[float]:
    """生成采样时间点（与参考版 CoachAnalyze.tsx 一致）"""
    lo, hi = 0.01, max(0.01, duration - 0.1)
    if mode == "single":
        hit = hit_time if hit_time is not None else duration / 2
        hit = min(max(lo, hit), hi)
        return [min(max(lo, hit + dt), hi) for dt in _SINGLE_OFFSETS]
    return [
        min(max(lo, duration * (i + 0.5) / _FULL_FRAME_COUNT), hi) for i in range(_FULL_FRAME_COUNT)
    ]


def _to_data_url(data: bytes) -> str:
    """JPEG bytes → dataURL"""
    import base64

    return f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"


def extract_frames(path: str, times: list[float], width: int = _FRAME_WIDTH) -> list[bytes]:
    """按采样时间点逐帧抽取，返回 JPEG bytes 列表"""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise FfmpegUnavailableError("ffmpeg 不可用")

    frames: list[bytes] = []
    for t in times:
        cmd = [
            ffmpeg,
            "-i",
            path,
            "-ss",
            f"{t:.3f}",
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-1",
            "-strict",
            "-1",
            "-q:v",
            str(_FRAME_QUALITY),
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        if proc.returncode != 0 or not proc.stdout:
            stderr_text = proc.stderr.decode(errors="replace")[-300:]
            log.warning(
                f"抽帧失败 time={t:.3f} returncode={proc.returncode} "
                f"stdout={len(proc.stdout)}B stderr={stderr_text}"
            )
            continue
        frames.append(proc.stdout)
    return frames


def process_video(path: str, mode: str, hit_time: float | None) -> dict:
    """编排：探测 → 校验时长 → 采样 → 抽帧 → 封面，返回抽帧结果 dict"""
    duration = probe_duration(path)
    frame_rate = probe_frame_rate(path)
    limit = _MAX_DURATION.get(mode, _MAX_DURATION["single"])
    if duration > limit:
        raise VideoTooLongError(
            message=f"{'单次挥拍' if mode == 'single' else '综合分析'}视频最长 "
            f"{int(limit)} 秒，当前 {duration:.1f} 秒"
        )

    times = build_sampling_times(mode, duration, hit_time)
    frames = extract_frames(path, times)
    if not frames:
        raise ValueError("未能抽取任何视频帧")

    # 封面帧：single 取击球瞬间（采样点中离 hit 最近帧），full 取中点帧
    hit = hit_time if hit_time is not None else duration / 2
    thumb_idx = min(range(len(times)), key=lambda i: abs(times[i] - hit))
    thumbnail = frames[thumb_idx]

    video_dir = os.path.dirname(path)
    frame_urls = []
    for i, frame in enumerate(frames):
        base = os.path.splitext(os.path.basename(path))[0]
        frame_name = f"{base}_f{i}.jpg"
        frame_path = os.path.join(video_dir, frame_name)
        with open(frame_path, "wb") as out:
            out.write(frame)
        rel_frame = os.path.relpath(frame_path, settings.UPLOAD_DIR).replace(os.sep, "/")
        frame_urls.append(f"videos/{rel_frame}")

    return {
        "frames": [_to_data_url(f) for f in frames],
        "frame_urls": frame_urls,
        "duration": duration,
        "frame_rate": frame_rate,
        "thumbnail": _to_data_url(thumbnail),
        "hit_time": hit,
        "mode": mode,
    }
