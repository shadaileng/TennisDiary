> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 75-3 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-13 |
> | 对应功能/内容 | MediaPipe 姿态推理 `POST /api/pose/analyze`（33 关键点 + 角度测量） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-13 | v1.0.0 | 初版（承接 [75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) §4.4） |
> | 2026-08-13 | v1.0.0 | 实施完成：17 用例 + 全量 219 passed，ruff 通过 |
>
> **关联文档**：[75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) · [75-2 视频上传与抽帧](./75-2-视频上传与抽帧.md) · [75-1 AI 评分代理接口](./75-1-AI评分代理接口.md)

# 75-3：MediaPipe 姿态推理

## 一、背景与目标

总纲 75-B2 §4.4：将浏览器端 WASM 姿态识别（`pose.ts`）迁移为服务端 MediaPipe Python（CPU 推理）。小程序上传视频抽帧后，后端对关键帧做姿态推理，输出 BlazePose 33 关键点与三个关键角度，供 AI 评分（75-1）降级路径与本地报告使用。

| 目标 | 说明 |
|------|------|
| 端点 | `POST /api/pose/analyze`（鉴权 `get_current_user`） |
| 入参 | `frames`（base64/dataURL JPEG 数组） |
| 出参 | 每帧 `landmarks[33]`（归一化坐标 + visibility）+ 首个可测帧的 `metrics{elbowAngle, kneeAngle, trunkLean}` |
| 模型 | `pose_landmarker_lite.task`（float16），随包路径 `server/models/`，CPU 推理 |
| 降级 | mediapipe 未安装 / 模型缺失 / 无人检测 → 返回空结果（AI 侧走本地降级） |

## 二、现状

| 项 | 现状 |
|----|------|
| 依赖 | **无 `mediapipe`**（需新增，体积大；测试环境不强制安装，用 monkeypatch 隔离） |
| 模型 | `server/models/` 目录不存在，需创建并放置 `pose_landmarker_lite.task`（约 5.7MB） |
| 配置 | `config.py` 无姿态模型路径，需新增 `POSE_MODEL_PATH` |
| 参考资产 | `pose.ts`：`CONNECTIONS`（BlazePose 33 点连接表）、`measureAngles`（肘角/膝角/躯干倾角，取可见度更高一侧） |

## 三、关键契约

- **33 关键点索引**（BlazePose 标准，`pose.ts` 连接表沿用）：

```
11 左肩  12 右肩  13 左肘  14 右肘  15 左腕  16 右腕
23 左髋  24 右髋  25 左膝  26 右膝  27 左踝  28 右踝
```

- **角度测量**（与 `pose.ts` `measureAngles` 一致）：

```
elbowAngle = angleAt(肩, 肘, 腕)   # 取可见度更高一侧
kneeAngle  = angleAt(髋, 膝, 踝)
trunkLean  = atan2(肩中点x-髋中点x, 髋中点y-肩中点y) 转为角度
```

- **出参**：

```json
{
  "code": 0, "message": "ok", "success": true,
  "data": {
    "frames": [
      {"landmarks": [{"x": 0.5, "y": 0.3, "z": 0.0, "visibility": 0.9}, ... 33 项]},
      ...
    ],
    "metrics": {"elbowAngle": 95.2, "kneeAngle": 140.1, "trunkLean": 8.3},  // 取首个可测帧，无可测则 null
    "detected": true
  }
}
```

- **降级**：mediapipe 不可用 / 模型缺失 → 503 或空结果（`detected=false`）。

## 四、详细方案

### 4.1 配置（`server/app/core/config.py`）

新增：

```python
# MediaPipe 姿态模型
POSE_MODEL_PATH: str = os.getenv("POSE_MODEL_PATH", f"{Path(__file__).resolve().parent.parent.parent}/models/pose_landmarker_lite.task")
```

> `server/models/pose_landmarker_lite.task` 随镜像打包（Dockerfile COPY），避免运行时下载失败。

### 4.2 服务层（新建 `server/app/services/pose_service.py`）

| 函数 | 职责 |
|------|------|
| `find_model()` | 检查 `settings.POSE_MODEL_PATH` 存在，返回路径或 `None` |
| `_get_landmarker()` | 懒加载 `mediapipe.tasks.python.vision.PoseLandmarker`（`RunningMode.IMAGE`，CPU，`num_poses=1`）；失败抛 `PoseUnavailableError` |
| `detect_pose(image_bytes)` | JPEG bytes → `mp.Image` → `detect` → 返回 33 关键点列表（含 visibility）或 `None`（无人检测） |
| `measure_angles(landmarks)` | 与 `pose.ts` 一致：肘角/膝角/躯干倾角（取可见度更高一侧，visibility 阈值 0.4） |
| `analyze_frames(frames)` | 逐帧推理，返回 `{frames: [...], metrics, detected}` |

要点：

- `mediapipe` 导入放函数内（懒加载），`importlib.util.find_spec("mediapipe")` 预检，未安装直接抛 `PoseUnavailableError`（路由转 503/降级），避免应用启动即崩溃；
- 关键点字典：`{"x", "y", "z", "visibility"}`，`z` 由 mp 返回（相对深度）；
- `measure_angles` 需要 `lms[11..28]` 关键点齐全且 visibility ≥ 0.4，否则跳过该帧测量；
- `analyze_frames` 对每个输入帧跑一次 `detect_pose`，`metrics` 取首个有完整关键点的帧。

### 4.3 路由（新建 `server/app/routers/pose.py`）

- `POST /api/pose/analyze`，`APIRouter(prefix="/api/pose", tags=["pose"])`；
- 请求体：`frames: list[str]`（base64/dataURL，`min_length=1`）；
- 流程：
  1. `find_model()` 为 `None` 或 mediapipe 未安装 → 503（detail 提示模型缺失）；
  2. `analyze_frames(frames)` 成功 → `ApiResponse(data={frames, metrics, detected})`；
  3. 无人检测 → 200 + `detected=false` + `metrics=null`（不报错）；
  4. 异常 → 400（frame 解码失败）或 503（推理服务不可用）。
- 注册 `main.py`：`from app.routers import pose` + `app.include_router(pose.router)`。

### 4.4 依赖

- `pyproject.toml`：新增 `mediapipe>=0.10.14`（主依赖）；
- Dockerfile：`COPY models/ /app/models/`（随镜像打包，后续 75-6 部署时统一处理）。

## 五、文件改动清单

| 文件 | 改动 |
|------|------|
| `server/app/services/pose_service.py` | 新建：find_model / detect_pose / measure_angles / analyze_frames |
| `server/app/routers/pose.py` | 新建：`POST /api/pose/analyze` |
| `server/app/core/config.py` | 新增 `POSE_MODEL_PATH` |
| `server/app/main.py` | 注册 `pose.router` |
| `server/pyproject.toml` | 新增 `mediapipe` |
| `server/models/.gitkeep` | 新建目录占位（模型文件不纳入版本管理） |
| `server/tests/routers/test_pose.py` | 新建：单测 + 接口测试 |
| `docs/README.md` / `docs/.vitepress/config.mts` | 同步条目（Phase B2 分组） |

## 六、测试计划（TDD）

**RED（先写测试，确认失败）** — `server/tests/routers/test_pose.py`：

| 用例 | 断言 |
|------|------|
| `measure_angles` 直角肘 | 肘角 ≈ 90° |
| `measure_angles` 伸直膝 | 膝角 ≈ 180° |
| `measure_angles` 躯干倾角 | 肩髋中点偏移 → 非零 |
| `measure_angles` visibility 不足 | 跳过 → 无测量 |
| `analyze_frames` 正常 | monkeypatch `detect_pose` → frames + metrics + detected=true |
| `analyze_frames` 无人检测 | monkeypatch `detect_pose=None` → detected=false |
| `analyze` 模型缺失 | monkeypatch `find_model=None` → 503 |
| `analyze` 成功 | monkeypatch `analyze_frames` → 200 + landmarks 33 项 |
| `analyze` 未登录 | → 401/403 |

> mediapipe 为重型依赖，测试环境不实际推理：全部用 monkeypatch 隔离，`measure_angles` 纯函数直接测。

## 七、验收标准

- [x] `POST /api/pose/analyze` 返回每帧 33 关键点 + metrics（首个可测帧）；
- [x] 模型缺失 → 503 且提示清晰；无人检测 → 200 + `detected=false`；
- [x] `measure_angles` 与参考版 `pose.ts` 输出一致（肘/膝/躯干角）；
- [x] 未登录返回 401/403；
- [x] `uv run pytest` 全绿、`ruff check` 无错误。

## 八、实施步骤

1. 编写本方案文档（📋）；
2. RED：`test_pose.py` 先行，确认失败；
3. GREEN：config 新增路径 → `pose_service.py` → `routers/pose.py` → main 注册 → pyproject 依赖；
4. REFACTOR + 回归：`uv run pytest` / `ruff check` 全绿，方案状态 🏁，同步 README / 侧边栏。

## 九、风险与注意事项

| 风险 | 说明与对策 |
|------|-----------|
| mediapipe 体积大/安装慢 | 仅生产安装；测试用 monkeypatch；Docker 层缓存 |
| CPU 推理慢 | lite 模型 + 帧数受限（≤8）；必要时降采样 |
| 模型文件缺失 | `find_model` 预检 → 503；模型随镜像打包 |
| 无人检测 | 返回 `detected=false`，AI 侧走本地降级报告（75-1 已有） |
