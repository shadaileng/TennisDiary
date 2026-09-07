"""MediaPipe 姿态推理服务层（CPU 推理，33 关键点 + 角度测量）

参考 Web 版 pose.ts：BlazePose 33 关键点连接表、measureAngles（肘/膝/躯干角）。
mediapipe 为重型依赖，导入放函数内懒加载（find_spec 预检），
模型文件缺失 / mediapipe 未安装时不阻塞应用启动，由路由层转 503/降级。
"""

import base64
import importlib.util
import math
import os
import subprocess

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("user")

# 可见度阈值：低于此值认为关键点不可靠，跳过角度测量（与 pose.ts 一致）
VISIBILITY_THRESHOLD = 0.4

# 骨架绘制颜色（对齐 Web pose.ts LIME #C8DA2B / 白关节点）
_SKELETON_COLOR = (200, 218, 43)
_JOINT_COLOR = (255, 255, 255)

# 骨架连线（Web pose.ts CONNECTIONS）
_CONNECTIONS = [
    [11, 12],
    [11, 13],
    [13, 15],
    [15, 17],
    [15, 19],
    [15, 21],
    [12, 14],
    [14, 16],
    [16, 18],
    [16, 20],
    [16, 22],
    [11, 23],
    [12, 24],
    [23, 24],
    [23, 25],
    [25, 27],
    [27, 29],
    [27, 31],
    [24, 26],
    [26, 28],
    [28, 30],
    [28, 32],
]

# 绘制关节点（11..28）
_JOINT_INDICES = list(range(11, 29))

# 关键点索引（BlazePose 标准）
_SHOULDER_L, _SHOULDER_R = 11, 12
_ELBOW_L, _ELBOW_R = 13, 14
_WRIST_L, _WRIST_R = 15, 16
_HIP_L, _HIP_R = 23, 24
_KNEE_L, _KNEE_R = 25, 26
_ANKLE_L, _ANKLE_R = 27, 28

# 参与角度测量的关键点索引范围（11..28）
_MEASURE_RANGE = range(_SHOULDER_L, _ANKLE_R + 1)


class PoseUnavailableError(RuntimeError):
    """MediaPipe 未安装或姿态模型缺失"""


def mediapipe_available() -> bool:
    """mediapipe 是否已安装（不实际导入）"""
    return importlib.util.find_spec("mediapipe") is not None


def find_model() -> str | None:
    """检查姿态模型文件是否存在，返回路径或 None"""
    path = settings.POSE_MODEL_PATH
    if path and os.path.isfile(path):
        return path
    return None


def is_available() -> bool:
    """服务可用性：mediapipe 已安装且模型文件存在"""
    return mediapipe_available() and find_model() is not None


_landmarker = None


def _get_landmarker():
    """懒加载 PoseLandmarker（RunningMode.IMAGE，CPU，num_poses=1）"""
    global _landmarker
    if _landmarker is not None:
        return _landmarker
    model = find_model()
    if not model:
        raise PoseUnavailableError("姿态模型缺失，请检查 POSE_MODEL_PATH")
    if not mediapipe_available():
        raise PoseUnavailableError("mediapipe 未安装")
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
    )
    _landmarker = vision.PoseLandmarker.create_from_options(options)
    log.info("MediaPipe PoseLandmarker 加载完成", model=model)
    return _landmarker


def detect_pose(image_bytes: bytes) -> list[dict] | None:
    """对单张 JPEG 推理，返回 33 关键点列表（含 visibility）或 None（无人检测）"""
    landmarker = _get_landmarker()
    from mediapipe import Image as MpImage

    # Pillow 解码 JPEG → numpy array → MediaPipe Image（避免 bytes 直传的格式歧义）
    image = mp_image_from_bytes(image_bytes, MpImage)
    result = landmarker.detect(image)

    if not result.pose_landmarks:
        return None
    pose = result.pose_landmarks[0]
    return [
        {
            "x": float(lm.x),
            "y": float(lm.y),
            "z": float(lm.z),
            "visibility": float(lm.visibility),
        }
        for lm in pose
    ]


def mp_image_from_bytes(image_bytes: bytes, mp_image_cls):
    """JPEG bytes → MediaPipe Image（Pillow 解码为 RGB ndarray）"""
    import io

    import mediapipe as mp
    import numpy as np
    from PIL import Image

    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    array = np.asarray(pil_img)
    return mp_image_cls(image_format=mp.ImageFormat.SRGB, data=array)


def _angle_at(a: dict, b: dict, c: dict) -> float:
    """夹角计算（与 pose.ts angleAt 一致），返回角度"""
    v1 = (a["x"] - b["x"], a["y"] - b["y"])
    v2 = (c["x"] - b["x"], c["y"] - b["y"])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    m1 = math.hypot(v1[0], v1[1])
    m2 = math.hypot(v2[0], v2[1])
    if not m1 or not m2:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (m1 * m2)))))


def measure_angles(landmarks: list[dict]) -> dict | None:
    """角度测量：肘角 / 膝角 / 躯干倾角（取可见度更高一侧）

    关键点数量不足或 visibility < 0.4 时返回 None（跳过该帧测量）。
    与 pose.ts measureAngles 输出一致。
    """
    if len(landmarks) < _ANKLE_R + 1:
        return None
    for i in _MEASURE_RANGE:
        lm = landmarks[i]
        if lm is None or lm.get("visibility", 0) < VISIBILITY_THRESHOLD:
            return None

    right_vis = landmarks[_ELBOW_R].get("visibility", 0) + landmarks[_KNEE_R].get("visibility", 0)
    left_vis = landmarks[_ELBOW_L].get("visibility", 0) + landmarks[_KNEE_L].get("visibility", 0)
    use_right = right_vis >= left_vis

    if use_right:
        elbow = _angle_at(landmarks[_SHOULDER_R], landmarks[_ELBOW_R], landmarks[_WRIST_R])
        knee = _angle_at(landmarks[_HIP_R], landmarks[_KNEE_R], landmarks[_ANKLE_R])
    else:
        elbow = _angle_at(landmarks[_SHOULDER_L], landmarks[_ELBOW_L], landmarks[_WRIST_L])
        knee = _angle_at(landmarks[_HIP_L], landmarks[_KNEE_L], landmarks[_ANKLE_L])

    shoulder_mid = {
        "x": (landmarks[_SHOULDER_L]["x"] + landmarks[_SHOULDER_R]["x"]) / 2,
        "y": (landmarks[_SHOULDER_L]["y"] + landmarks[_SHOULDER_R]["y"]) / 2,
    }
    hip_mid = {
        "x": (landmarks[_HIP_L]["x"] + landmarks[_HIP_R]["x"]) / 2,
        "y": (landmarks[_HIP_L]["y"] + landmarks[_HIP_R]["y"]) / 2,
    }
    trunk_lean = math.degrees(
        math.atan2(shoulder_mid["x"] - hip_mid["x"], hip_mid["y"] - shoulder_mid["y"])
    )
    return {
        "elbowAngle": round(elbow, 1),
        "kneeAngle": round(knee, 1),
        "trunkLean": round(trunk_lean, 1),
    }


def _decode_frame(frame: str) -> bytes:
    """解析 base64/dataURL → JPEG bytes；非法抛 ValueError"""
    payload = frame.split(",", 1)[1] if "," in frame else frame
    try:
        return base64.b64decode(payload)
    except Exception as exc:
        raise ValueError("帧数据不是有效的 base64") from exc


def _load_frames_from_urls(frame_urls: list[str]) -> list[str]:
    """从文件路径读取帧，返回 base64 dataURL 列表"""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    frames = []
    for url in frame_urls:
        path = os.path.normpath(os.path.join(upload_dir, url))
        if os.path.isfile(path):
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            frames.append(f"data:image/jpeg;base64,{data}")
    return frames


def draw_skeleton(image_bytes: bytes, landmarks: list[dict]) -> bytes:
    """在帧上叠加绘制 Pose 骨架（对齐 Web drawSkeleton），返回新 JPEG bytes

    - 低可见度（< 0.4）连接线/关节点跳过绘制
    - 髋部重心 + 十字准星标记
    """
    import io

    from PIL import Image, ImageDraw

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("帧图像解码失败") from exc
    w, h = img.size
    draw = ImageDraw.Draw(img)

    def visible(idx: int) -> bool:
        if idx >= len(landmarks) or landmarks[idx] is None:
            return False
        return landmarks[idx].get("visibility", 0) >= VISIBILITY_THRESHOLD

    def point(idx: int) -> tuple[float, float]:
        lm = landmarks[idx]
        return (lm["x"] * w, lm["y"] * h)

    line_width = max(2, int(w / 320))
    joint_radius = max(2.5, w / 260)

    # 连接线
    for a, b in _CONNECTIONS:
        if not (visible(a) and visible(b)):
            continue
        draw.line([point(a), point(b)], fill=_SKELETON_COLOR, width=line_width, joint="curve")

    # 关节点
    for i in _JOINT_INDICES:
        if not visible(i):
            continue
        px, py = point(i)
        draw.ellipse(
            [px - joint_radius, py - joint_radius, px + joint_radius, py + joint_radius],
            fill=_JOINT_COLOR,
        )

    # 髋部重心标记
    if visible(_HIP_L) and visible(_HIP_R):
        lh, rh = point(_HIP_L), point(_HIP_R)
        cx, cy = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
        r = max(6, w / 90)
        cross = max(1, int(w / 500))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_JOINT_COLOR, width=cross)
        draw.ellipse([cx - r / 2.4, cy - r / 2.4, cx + r / 2.4, cy + r / 2.4], fill=_SKELETON_COLOR)
        draw.line([cx - r * 1.6, cy, cx + r * 1.6, cy], fill=_JOINT_COLOR, width=cross)
        draw.line([cx, cy - r * 1.6, cx, cy + r * 1.6], fill=_JOINT_COLOR, width=cross)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def _resolve_video_dir(video_url: str) -> tuple[str, str] | None:
    """校验并解析 video_url（相对 UPLOAD_DIR）→ (视频所在目录绝对路径, 文件名 base)

    路径穿越 / 文件不存在 / 非 UPLOAD_DIR 内 → 返回 None（调用方抛 ValueError）。
    """
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    candidate = os.path.normpath(os.path.join(upload_dir, video_url))
    if candidate == upload_dir or not candidate.startswith(upload_dir + os.sep):
        return None
    if not os.path.isfile(candidate):
        return None
    base = os.path.splitext(os.path.basename(candidate))[0]
    return os.path.dirname(candidate), base


def _should_use_full_frames(
    full_frames: bool | None,
    save_skeleton: bool,
    video_url: str | None,
    duration: float | None,
) -> bool:
    """判断是否使用逐帧生成骨架视频

    优先级：
    1. 前端参数 full_frames=true  → 强制逐帧
    2. 前端参数 full_frames=false → 强制抽样
    3. 配置 pose.full_frames_enabled=false → 禁用自动，走抽样
    4. duration ≤ pose.full_frames_threshold → 自动逐帧
    5. 其他 → 抽样（7-8帧）
    """
    if not save_skeleton or not video_url:
        return False

    # 显式指定
    if full_frames is True:
        return True
    if full_frames is False:
        return False

    # 检查配置是否启用
    if not settings.POSE_FULL_FRAMES_ENABLED:
        return False

    # 自动判断：时长 ≤ 阈值
    threshold = settings.POSE_FULL_FRAMES_THRESHOLD
    if threshold > 0 and duration is not None and duration <= threshold:
        return True

    return False


def _rel_url(abs_path: str) -> str:
    """UPLOAD_DIR 内绝对路径 → 相对 URL（正斜杠）- 使用 file_service 门面"""
    from app.services import file_service

    return file_service.rel_of(abs_path)


def find_ffmpeg() -> str | None:
    """定位 ffmpeg 可执行文件：系统 PATH → imageio-ffmpeg 自带二进制"""
    from shutil import which

    system = which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.isfile(bundled):
            return bundled
    except (ImportError, OSError) as e:
        log.debug(f"imageio_ffmpeg 探测失败: {e}")
    return None


def _extract_first_frame(video_path: str, out_path: str) -> bool:
    """从视频提取首帧保存为 JPEG，返回是否成功"""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return False
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", video_path, "-vframes", "1", "-q:v", "2", out_path],
        capture_output=True,
        timeout=30,
    )
    return proc.returncode == 0 and os.path.isfile(out_path)


def extract_all_frames(video_path: str, width: int = 640) -> list[bytes]:
    """从视频文件逐帧抽取所有帧，返回 JPEG bytes 列表"""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return []

    cmd = [
        ffmpeg,
        "-i",
        video_path,
        "-vf",
        f"scale={width}:-1",
        "-q:v",
        "2",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=300)
    if proc.returncode != 0:
        log.warning("逐帧抽取失败", rc=proc.returncode)
        return []

    # 分割 JPEG 帧（FFDFFD8 开头）
    frames = []
    data = proc.stdout
    start = 0
    while start < len(data):
        # 查找下一个 JPEG SOI 标记
        next_start = data.find(b"\xff\xd8", start + 1)
        if next_start == -1:
            frame = data[start:]
        else:
            frame = data[start:next_start]
        if len(frame) > 100:  # 过滤碎片
            frames.append(frame)
        if next_start == -1:
            break
        start = next_start
    return frames


def analyze_video_file(
    video_path: str,
    video_url: str,
    frame_rate: float | None = None,
) -> dict:
    """从视频文件逐帧读取并处理，生成骨架视频（帧数与原视频一致）

    返回 {frames, metrics, detected, skeleton_video_url, skeleton_thumb}
    """
    from app.services import file_service

    frames = extract_all_frames(video_path)
    if not frames:
        raise ValueError("未能从视频中抽取任何帧")

    video_dir = os.path.dirname(video_path)
    base = os.path.splitext(os.path.basename(video_path))[0]

    results: list[dict] = []
    metrics = None
    detected = False
    skeleton_paths: list[str] = []

    for i, frame_bytes in enumerate(frames):
        landmarks = detect_pose(frame_bytes)
        if landmarks is None:
            results.append({"landmarks": []})
        else:
            detected = True
            results.append({"landmarks": landmarks})
            if metrics is None:
                metrics = measure_angles(landmarks)

        # 生成骨架帧
        if landmarks is not None:
            sk_bytes = draw_skeleton(frame_bytes, landmarks)
        else:
            sk_bytes = frame_bytes
        sk_path = os.path.join(video_dir, f"{base}_sk{i:04d}.jpg")
        file_service.write_bytes(sk_path, sk_bytes)
        skeleton_paths.append(sk_path)

    # 编码骨架视频（帧率 = 帧数 / 时长，确保播放时长与原视频一致）
    skeleton_video_url = None
    skeleton_thumb = _rel_url(skeleton_paths[0]) if skeleton_paths else None

    if skeleton_paths and frame_rate:
        # 用原视频帧率编码，帧数一致则播放时长一致
        effective_fps = max(1.0, frame_rate)
        out_name = f"{base}_skeleton.mp4"
        out_path = os.path.join(video_dir, out_name)
        encoded = encode_skeleton_video(skeleton_paths, out_path, effective_fps)
        if encoded and os.path.isfile(out_path):
            skeleton_video_url = _rel_url(out_path)

    return {
        "frames": results,
        "metrics": metrics,
        "detected": detected,
        "skeleton_video_url": skeleton_video_url,
        "skeleton_thumb": skeleton_thumb,
    }


def encode_skeleton_video(skeleton_paths: list[str], out_path: str, fps: float) -> bool:
    """用 ffmpeg 将骨架帧序列编码为 H.264 mp4（微信可播）；失败返回 False 不抛错

    帧数不足 2 / ffmpeg 不可用 → False；编码成功且产物存在 → True。

    使用 -framerate + %04d 通配符直接读图片序列（而非 concat demuxer），
    避免静态 JPEG 被 concat 视为"无限长"导致输出只有 1 帧的 bug。
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg or len(skeleton_paths) < 2:
        return False

    # 骨架帧已按 {base}_sk{idx:04d}.jpg 命名，构建 %04d 通配符输入路径
    first_frame = skeleton_paths[0]
    frame_dir = os.path.dirname(first_frame)
    frame_base = os.path.splitext(os.path.basename(first_frame))[0]  # e.g. "abc_sk0000"
    pattern = os.path.join(frame_dir, f"{frame_base.rsplit('_sk', 1)[0]}_sk%04d.jpg")

    effective_fps = max(1.0, fps)
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(effective_fps),
        "-i",
        pattern,
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    ok = proc.returncode == 0 and os.path.isfile(out_path)
    if not ok:
        log.warning("骨架视频编码失败", rc=proc.returncode, err=(proc.stderr or b"")[:300])
    return ok


def analyze_frames(
    frames: list[str] | None = None,
    video_url: str | None = None,
    save_skeleton: bool = False,
    duration: float | None = None,
    frame_rate: float | None = None,
    full_frames: bool | None = None,
    frame_urls: list[str] | None = None,
) -> dict:
    """逐帧推理编排，返回 {frames, metrics, detected, skeleton_*}

    - frames: 每帧 {landmarks: [...]}（无人检测帧 landmarks 为空数组）
    - metrics: 取首个可测帧的 {elbowAngle, kneeAngle, trunkLean}，无可测帧为 None
    - detected: 是否至少有一帧检测到人
    - skeleton_frames: 骨架帧相对 URL 数组（仅 save_skeleton + video_url 时）
    - skeleton_video_url: 骨架关键帧动画 mp4 相对 URL（ffmpeg 可用时）
    - skeleton_thumb: 封面骨架帧相对 URL（取首次可测帧，否则第一帧）
    - full_frames: None=自动判断，true=强制逐帧，false=强制抽样
    - frame_urls: 帧文件相对路径数组（优先使用）
    """
    # 优先使用 frame_urls
    if frame_urls:
        frames = _load_frames_from_urls(frame_urls)
    if not frames:
        raise ValueError("无有效帧数据")

    # 判断是否使用逐帧生成
    use_full = _should_use_full_frames(full_frames, save_skeleton, video_url, duration)

    if use_full:
        # 逐帧生成：从视频文件读取全部帧
        return _analyze_full_frames(video_url, frame_rate)
    else:
        # 抽样生成：处理传入的 frames
        return _analyze_sampled_frames(frames, video_url, save_skeleton, duration, frame_rate)


def _analyze_full_frames(
    video_url: str | None,
    frame_rate: float | None,
) -> dict:
    """从视频文件逐帧读取并处理，生成骨架视频（帧数与原视频一致）"""
    if not video_url:
        raise ValueError("video_url 不能为空")

    resolved = _resolve_video_dir(video_url)
    if resolved is None:
        raise ValueError("video_url 非法或不存在")
    video_dir, base = resolved

    video_path = os.path.join(video_dir, f"{base}.mp4")
    if not os.path.isfile(video_path):
        raise ValueError("视频文件不存在")

    extracted_frames = extract_all_frames(video_path)
    if not extracted_frames:
        raise ValueError("未能从视频中抽取任何帧")

    from app.services import file_service

    results: list[dict] = []
    metrics = None
    detected = False
    skeleton_paths: list[str] = []
    skeleton_info: list[dict] = []  # 包含预计算 MD5/size

    for i, frame_bytes in enumerate(extracted_frames):
        landmarks = detect_pose(frame_bytes)
        if landmarks is None:
            results.append({"landmarks": []})
        else:
            detected = True
            results.append({"landmarks": landmarks})
            if metrics is None:
                metrics = measure_angles(landmarks)

        # 生成骨架帧
        if landmarks is not None:
            sk_bytes = draw_skeleton(frame_bytes, landmarks)
        else:
            sk_bytes = frame_bytes
        sk_path = os.path.join(video_dir, f"{base}_sk{i:04d}.jpg")
        file_service.write_bytes(sk_path, sk_bytes)

        # 预计算 MD5 + size（一次磁盘读取）
        md5, size = file_service.md5_and_size_of(sk_path)

        skeleton_paths.append(sk_path)
        skeleton_info.append(
            {
                "rel_path": _rel_url(sk_path),
                "md5": md5,
                "size": size,
                "upload_source": "skeleton_frame",
            }
        )

    # 编码骨架视频
    skeleton_video_url = None
    skeleton_video_info = None
    skeleton_thumb = None
    skeleton_thumb_info = None

    if skeleton_paths and frame_rate:
        effective_fps = max(1.0, frame_rate)
        out_name = f"{base}_skeleton.mp4"
        out_path = os.path.join(video_dir, out_name)
        encoded = encode_skeleton_video(skeleton_paths, out_path, effective_fps)
        if encoded and os.path.isfile(out_path):
            skeleton_video_url = _rel_url(out_path)
            md5, size = file_service.md5_and_size_of(out_path)
            skeleton_video_info = {
                "rel_path": skeleton_video_url,
                "md5": md5,
                "size": size,
                "upload_source": "skeleton_video",
            }

            # 提取骨架视频首帧作为永久缩略图（独立文件，不依赖 sk*.jpg）
            thumb_name = f"{base}_thumb.jpg"
            thumb_path = os.path.join(video_dir, thumb_name)
            _extract_first_frame(out_path, thumb_path)
            if os.path.isfile(thumb_path):
                md5, size = file_service.md5_and_size_of(thumb_path)
                skeleton_thumb = _rel_url(thumb_path)
                skeleton_thumb_info = {
                    "rel_path": skeleton_thumb,
                    "md5": md5,
                    "size": size,
                    "upload_source": "skeleton_thumb",
                }

    return {
        "frames": results,
        "metrics": metrics,
        "detected": detected,
        "skeleton_frames": skeleton_info,
        "skeleton_video_url": skeleton_video_url,
        "skeleton_video_info": skeleton_video_info,
        "skeleton_thumb": skeleton_thumb,
        "skeleton_thumb_info": skeleton_thumb_info,
    }


def _analyze_sampled_frames(
    frames: list[str],
    video_url: str | None,
    save_skeleton: bool,
    duration: float | None,
    frame_rate: float | None,
) -> dict:
    """处理抽样的帧（原有逻辑）"""
    from app.services import file_service

    results: list[dict] = []
    metrics = None
    detected = False
    metrics_sk_idx: int | None = None
    skeleton_paths: list[str] = []
    skeleton_info: list[dict] = []  # 包含预计算 MD5/size
    skeleton_thumb = None
    skeleton_thumb_info = None
    skeleton_video_url = None
    skeleton_video_info = None

    video_dir = None
    base = None
    if save_skeleton and video_url:
        resolved = _resolve_video_dir(video_url)
        if resolved is None:
            raise ValueError("video_url 非法或不存在")
        video_dir, base = resolved

    sk_idx = 0
    for _i, frame in enumerate(frames):
        image_bytes = _decode_frame(frame)
        landmarks = detect_pose(image_bytes)
        if landmarks is None:
            results.append({"landmarks": []})
        else:
            detected = True
            results.append({"landmarks": landmarks})
            if metrics is None:
                metrics = measure_angles(landmarks)
                metrics_sk_idx = sk_idx
        # 所有帧都生成骨架帧：有人绘制骨架，无人使用原图
        if save_skeleton and video_dir is not None:
            if landmarks is not None:
                sk_bytes = draw_skeleton(image_bytes, landmarks)
            else:
                sk_bytes = image_bytes  # 无人检测时使用原图
            sk_path = os.path.join(video_dir, f"{base}_sk{sk_idx:04d}.jpg")
            file_service.write_bytes(sk_path, sk_bytes)

            # 预计算 MD5 + size（一次磁盘读取）
            md5, size = file_service.md5_and_size_of(sk_path)

            skeleton_paths.append(sk_path)
            skeleton_info.append(
                {
                    "rel_path": _rel_url(sk_path),
                    "md5": md5,
                    "size": size,
                    "upload_source": "skeleton_frame",
                }
            )
            sk_idx += 1

    if skeleton_info:
        if metrics_sk_idx is not None and metrics_sk_idx < len(skeleton_info):
            skeleton_thumb_info = skeleton_info[metrics_sk_idx]
        else:
            skeleton_thumb_info = skeleton_info[0]
        skeleton_thumb = skeleton_thumb_info["rel_path"]
    if skeleton_paths and video_dir is not None:
        # 骨骼视频帧率 = 帧数/时长，确保播放时长与原视频一致
        effective_fps = (len(skeleton_paths) / duration) if duration else 2.0
        out_name = f"{base}_skeleton.mp4"
        out_path = os.path.join(video_dir, out_name)
        encoded = encode_skeleton_video(skeleton_paths, out_path, effective_fps)
        if encoded and os.path.isfile(out_path):
            skeleton_video_url = _rel_url(out_path)
            md5, size = file_service.md5_and_size_of(out_path)
            skeleton_video_info = {
                "rel_path": skeleton_video_url,
                "md5": md5,
                "size": size,
                "upload_source": "skeleton_video",
            }

            # 提取骨架视频首帧作为永久缩略图（独立文件，不依赖 sk*.jpg）
            thumb_name = f"{base}_thumb.jpg"
            thumb_path = os.path.join(video_dir, thumb_name)
            _extract_first_frame(out_path, thumb_path)
            if os.path.isfile(thumb_path):
                md5, size = file_service.md5_and_size_of(thumb_path)
                skeleton_thumb = _rel_url(thumb_path)
                skeleton_thumb_info = {
                    "rel_path": skeleton_thumb,
                    "md5": md5,
                    "size": size,
                    "upload_source": "skeleton_thumb",
                }

    return {
        "frames": results,
        "metrics": metrics,
        "detected": detected,
        "skeleton_frames": skeleton_info,
        "skeleton_video_url": skeleton_video_url,
        "skeleton_video_info": skeleton_video_info,
        "skeleton_thumb": skeleton_thumb,
        "skeleton_thumb_info": skeleton_thumb_info,
    }
