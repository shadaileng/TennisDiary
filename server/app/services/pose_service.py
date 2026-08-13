"""MediaPipe 姿态推理服务层（CPU 推理，33 关键点 + 角度测量）

参考 Web 版 pose.ts：BlazePose 33 关键点连接表、measureAngles（肘/膝/躯干角）。
mediapipe 为重型依赖，导入放函数内懒加载（find_spec 预检），
模型文件缺失 / mediapipe 未安装时不阻塞应用启动，由路由层转 503/降级。
"""

import base64
import importlib.util
import math
import os

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("user")

# 可见度阈值：低于此值认为关键点不可靠，跳过角度测量（与 pose.ts 一致）
VISIBILITY_THRESHOLD = 0.4

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
    from mediapipe.tasks.python import vision

    options = vision.PoseLandmarkerOptions(
        base_options=vision.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
    )
    _landmarker = vision.PoseLandmarker.create_from_options(options)
    log.info("MediaPipe PoseLandmarker 加载完成", model=model)
    return _landmarker


def detect_pose(image_bytes: bytes) -> list[dict] | None:
    """对单张 JPEG 推理，返回 33 关键点列表（含 visibility）或 None（无人检测）"""
    landmarker = _get_landmarker()
    from mediapipe.tasks.python.core.image import Image as MpImage

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

    import numpy as np
    from PIL import Image

    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    array = np.asarray(pil_img)
    return mp_image_cls(image_format=mp_image_cls.ImageFormat.SRGB, data=array)


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


def analyze_frames(frames: list[str]) -> dict:
    """逐帧推理编排，返回 {frames, metrics, detected}

    - frames: 每帧 {landmarks: [...]}（无人检测帧 landmarks 为空数组）
    - metrics: 取首个可测帧的 {elbowAngle, kneeAngle, trunkLean}，无可测帧为 None
    - detected: 是否至少有一帧检测到人
    """
    results: list[dict] = []
    metrics = None
    detected = False
    for frame in frames:
        image_bytes = _decode_frame(frame)
        landmarks = detect_pose(image_bytes)
        if landmarks is None:
            results.append({"landmarks": []})
            continue
        detected = True
        results.append({"landmarks": landmarks})
        if metrics is None:
            metrics = measure_angles(landmarks)
    return {"frames": results, "metrics": metrics, "detected": detected}
