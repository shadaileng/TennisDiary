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

# 上传完整视频上限制（秒）：超长须先在相册裁短
_UPLOAD_MAX_DURATION = 180.0
# 片段/整片时长限制（秒）：与整片上传上限一致，不再按模式额外收紧
# （single=单次挥拍、full=综合分析；整片 ≤180s，裁剪后总长也 ≤180s）
_MAX_DURATION = {"single": _UPLOAD_MAX_DURATION, "full": _UPLOAD_MAX_DURATION}
# 单段最短（秒）
_MIN_SEGMENT_LEN = 0.6
# 每模式最大片段数
_MAX_SEGMENTS = {"single": 1, "full": 8}


class FfmpegUnavailableError(RuntimeError):
    """ffmpeg 二进制不可用"""


class VideoTooLongError(ValueError):
    """视频时长超过模式限制"""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class InvalidCutError(ValueError):
    """裁剪片段校验失败"""

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
    log.info(f"probe_duration: path={path} ffprobe={ffprobe}")
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
        log.info(f"ffprobe: rc={proc.returncode} stdout={proc.stdout.decode()!r} stderr={proc.stderr.decode()[-300:]!r}")
        if proc.returncode == 0:
            try:
                return float(proc.stdout.decode().strip())
            except ValueError:
                pass
        log.warning(f"ffprobe 探测时长失败 rc={proc.returncode} stderr={proc.stderr.decode('utf-8', 'replace')[-300:]}")
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        proc = subprocess.run([ffmpeg, "-i", path], capture_output=True, timeout=30)
        try:
            return _parse_duration_from_ffmpeg_stderr(proc.stderr.decode(errors="replace"))
        except ValueError:
            log.warning(f"ffmpeg 解析时长失败 rc={proc.returncode} stderr={proc.stderr.decode('utf-8', 'replace')[-300:]}")
            raise
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


def validate_cuts(cuts: list[dict], mode: str, duration: float) -> list[dict]:
    """校验并规范化裁剪片段列表，返回按 start 排序的片段 dict 列表

    规则：
    - 片段数 ≤ 模式上限（single 1 / full 8）
    - 每段 0 ≤ start < end ≤ duration，且长度 ≥ 0.6s
    - 片段按 start 升序且互不重叠（相邻可相切）
    - 拼接总长 ≤ 模式上限
    """
    if not isinstance(cuts, list):
        raise InvalidCutError("裁剪片段参数格式错误")
    limit = _MAX_DURATION.get(mode, _MAX_DURATION["single"])
    max_segments = _MAX_SEGMENTS.get(mode, _MAX_SEGMENTS["single"])
    if len(cuts) > max_segments:
        label = "单次挥拍" if mode == "single" else "综合分析"
        raise InvalidCutError(f"{label}最多选择 {max_segments} 个片段")

    ordered = sorted(cuts, key=lambda c: float(c.get("start", 0)))
    total = 0.0
    prev_end = 0.0
    for c in ordered:
        try:
            start = float(c["start"])
            end = float(c["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidCutError("裁剪片段缺少起点/终点") from exc
        if not (0 <= start < end <= duration):
            raise InvalidCutError("片段起点/终点超出视频范围")
        if end - start < _MIN_SEGMENT_LEN:
            raise InvalidCutError(f"片段最短 {_MIN_SEGMENT_LEN:.0f} 秒")
        if start < prev_end:
            raise InvalidCutError("片段存在重叠，请调整")
        prev_end = end
        total += end - start

    if total > limit:
        raise InvalidCutError(
            f"{'单次挥拍' if mode == 'single' else '综合分析'}片段总长最长 "
            f"{int(limit)} 秒，当前 {total:.1f} 秒"
        )
    return ordered


def trim_video(src: str, dst: str, start: float, length: float) -> None:
    """用 ffmpeg 精确 seek（输出端 seek）裁切片段并重编码为 H.264 mp4

    音频优先 `-c:a copy`（无需转码）；失败时降级丢弃音轨重试。
    精确 seek 对击球瞬间等时间点敏感，故用 `-ss` 放在 `-i` 之后（逐帧解码到起点）。
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise FfmpegUnavailableError("ffmpeg 不可用")

    base = [
        ffmpeg,
        "-y",
        "-i",
        src,
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{length:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]
    for extra in (["-c:a", "copy"], ["-an"]):
        cmd = [*base, *extra, dst]
        log.info(f"trim_video cmd={' '.join(cmd[:8])}... dst={dst}")
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        log.info(f"trim_video rc={proc.returncode} dst_exists={os.path.isfile(dst)} dst_size={os.path.getsize(dst) if os.path.isfile(dst) else 'N/A'} stderr={proc.stderr.decode('utf-8', errors='replace')[-500:]!r}")
        if proc.returncode == 0 and os.path.isfile(dst) and os.path.getsize(dst) > 0:
            return
    log.warning("视频片段裁切失败", start=start, length=length, src=src)
    raise InvalidCutError("视频片段裁切失败，请重试")


def trim_and_concat(src: str, cuts: list[dict], mode: str) -> str:
    """按裁剪片段列表逐个裁切并拼接为单个 mp4；返回最终输出路径

    产物与源文件同目录（`videos/{user}/`），片段命名为 `{base}_seg{i}.mp4`，
    多段时以 concat demuxer 拼接为 `{base}_concat.mp4`（失败降级重编码拼接）。
    """
    seg_dir = os.path.dirname(src)
    stem = os.path.splitext(os.path.basename(src))[0]

    seg_paths: list[str] = []
    try:
        for i, cut in enumerate(cuts):
            seg = os.path.join(seg_dir, f"{stem}_seg{i}.mp4")
            trim_video(src, seg, cut["start"], cut["end"] - cut["start"])
            seg_paths.append(seg)
        if len(seg_paths) == 1:
            return seg_paths[0]

        out = os.path.join(seg_dir, f"{stem}_concat.mp4")
        concat_list = os.path.join(seg_dir, f"{stem}_concat.txt")
        with open(concat_list, "w", encoding="utf-8") as fh:
            for seg in seg_paths:
                fh.write(f"file '{os.path.basename(seg)}'\n")

        ffmpeg = find_ffmpeg()
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                out,
            ],
            capture_output=True,
            timeout=180,
        )
        if proc.returncode != 0 or not os.path.isfile(out) or os.path.getsize(out) == 0:
            proc = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_list,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    "-c:a",
                    "copy",
                    out,
                ],
                capture_output=True,
                timeout=240,
            )
        if proc.returncode != 0 or not os.path.isfile(out) or os.path.getsize(out) == 0:
            raise InvalidCutError("视频片段拼接失败，请重试")
        return out
    finally:
        for seg in seg_paths:
            if os.path.isfile(seg):
                os.unlink(seg)
        leftover = os.path.join(seg_dir, f"{stem}_concat.txt")
        if os.path.isfile(leftover):
            os.unlink(leftover)


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


def process_video(
    path: str,
    mode: str,
    hit_time: float | None,
    cuts: list[dict] | None = None,
) -> dict:
    """编排：探测 → 整片时长校验（≤180s）→（可选）裁剪拼接 → 采样 → 抽帧 → 封面

    - 时长上限仅 _UPLOAD_MAX_DURATION（180s）统一兜底，不做模式差异收紧
    - cuts 提供时先裁切拼接（hit_time 视为拼接后相对时间），再对产物走上游流程
    - 返回 dict 含 trimmed（是否裁剪）与 segments（规范化后的片段列表）
    """
    duration = probe_duration(path)
    if duration > _UPLOAD_MAX_DURATION:
        raise VideoTooLongError(
            message=f"视频最长 {int(_UPLOAD_MAX_DURATION)} 秒，当前 {duration:.1f} 秒，"
            "请先在相册裁剪后再上传"
        )

    segments: list[dict] | None = None
    working = path
    log.info(f"process_video: cuts={cuts} duration={duration}")
    if cuts:
        segments = validate_cuts(cuts, mode, duration)
        log.info(f"validate_cuts OK: segments={segments}")
        working = trim_and_concat(path, segments, mode)
        log.info(f"trim_and_concat returned: working={working} exists={os.path.isfile(working)}")
        if working != path and os.path.isfile(path):
            os.unlink(path)  # 裁剪后原完整视频不再保留
        # 重探测裁剪产物的时长/帧率（拼接结果实际值）
        duration = probe_duration(working)
        frame_rate = probe_frame_rate(working)
    else:
        frame_rate = probe_frame_rate(path)

    # 时长上限仅由 _UPLOAD_MAX_DURATION（180s）在裁剪前统一兜底，
    # 整片/裁剪后总长均已 ≤180s，无需再按模式校验

    times = build_sampling_times(mode, duration, hit_time)
    frames = extract_frames(working, times)
    if not frames:
        raise ValueError("未能抽取任何视频帧")

    # 封面帧：single 取击球瞬间（采样点中离 hit 最近帧），full 取中点帧
    hit = hit_time if hit_time is not None else duration / 2
    thumb_idx = min(range(len(times)), key=lambda i: abs(times[i] - hit))
    thumbnail = frames[thumb_idx]

    video_dir = os.path.dirname(working)
    frame_urls = []
    for i, frame in enumerate(frames):
        base = os.path.splitext(os.path.basename(working))[0]
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
        "trimmed": bool(segments),
        "segments": segments,
    }
