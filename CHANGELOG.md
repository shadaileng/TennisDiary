# Changelog

本项目的所有显著变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.66.4] - 2026-08-20

### Fixed

- miniapp 时间轴交互改为**纵向分区**（99 时间轴）：上半区域拖动 → 拉播放头 scrub（seek 逐帧预览），下半区域拖动 → 平移视野 pan（仅滚 `viewStart`、不改播放头不 seek）；移除原「播放头 x 距离 ±10px」命中判定，改为 `barTop`/`barHeight` 测量 + 按 `touch.clientY` 判定；双指抬指剩单指时按剩余手指 y 重新分区；提示文案更新为「双指缩放 · 上拖播放头 / 下拖平移」。

## [1.66.3] - 2026-08-20

### Fixed

- miniapp 修复时间轴放大后无法观察目标片段（99 时间轴）：新增平移与居中能力——单指按下区分命中（播放头 ±10px 内 → scrub；空白/片段色块 → pan），`pan` 模式按 `Δx/barWidth × visibleSpan` 平移可见窗且不改播放头、不触发 seek；点击片段色块 → 视野居中该片段并预览中点帧（`centerOnSegment`）；统一 `clampViewStart` 汇集可见窗边界夹紧逻辑；提示文案更新为「双指缩放 / 拖动平移」。

## [1.66.2] - 2026-08-20

### Fixed

- miniapp 修复播放头拖动画面不预览（99 时间轴）：`videoCtx` 原在 `onMounted` 创建，视频元素尚未渲染导致 `seek` 静默失效——改在 `@loadedmetadata`（`onVideoMeta`）就绪后重新 `createVideoContext("swingVideo")` 并置 `videoReady`；拖动 seek 前校验就绪标记。新增暂停态**强制刷新帧** hack（`seekPreview`：`seek(t)` 后若未播放则 `play()+pause()`），解决微信开发者工具模拟器（Chromium 原生组件暂停态不重绘解码帧）与部分真机核对；`@play/@pause` 记录播放态，`onBarTouchEnd` 松手补帧（`flushPlayhead`）确保节流跳过的最后一帧精确落位。

## [1.66.1] - 2026-08-20

### Fixed

- miniapp 修复 `chooseVideo` 选视频失败回归（99 引入）：Step 99 将 `maxDuration` 误设为 180，触发微信选择器前置硬校验 `maxDuration can not over 60`，导致选择器无法弹出（Step 77 曾修复同类问题）。已移除 `maxDuration` 参数，相册长片不受限；整片 180s 上限改由选后 `dur > 180` 预检查 toast + 服务端 `_UPLOAD_MAX_DURATION` 校验兜底。

## [1.66.0] - 2026-08-20

### Added

- 电子教练时间轴多段剪辑（99）：小程序端 `analyze.vue` 新增自定义触摸时间轴——**双指捏合缩放**（可见窗最窄 2s，以播放头为锚点滚动）、**播放头单指拖动实时 `VideoContext.seek` 逐帧预览**（50ms 节流 + 边缘自动滚窗）、**多段起止标记**（`➕起点`/`✋终点` 按序闭合，single 限 1 段 / full ≤8 段，单段 ≥0.6s、不重叠、总长 ≤ 模式上限，可删段/重置）；`hit_time` 由前端按片段前缀长度换算为**拼接后相对时间**，落在片段间隙忽略并提示。
- 服务端 `POST /api/video/upload` 新增 `cuts` 表单字段（JSON 数组 `[{start,end}]`）：`video_service` 新增 `_UPLOAD_MAX_DURATION=180s` 整片上限、`validate_cuts` 权威校验、`trim_video`（ffmpeg 输出端精确 seek + libx264 重编码 + 音频 copy 兜底 `-an`）、`trim_and_concat`（截取 concat demuxer `-c copy` 拼接，失败降级重编码），裁切后删除原片并重探测时长/帧率，下游（报告视频/骨架视频/帧率适配）零改动；返回新增 `trimmed`/`segments`。后端全量 375 passed（含真实 ffmpeg 两段拼接用例）+ ruff 通过；miniapp `type-check` + `build:mp-weixin` 通过。

## [1.65.1] - 2026-08-19

### Fixed

- miniapp 修复 type-check 存量类型错误（8 项清零）：`Field.vue` 内联 `$event.detail.value` 被 vue-tsc 解析为 DOM `InputEvent.detail:number`，改为 `(e:any)=>e.detail.value` 处理器（与全库 `@input` 约定一致）；`LineChart.vue`/`RadarChart.vue` 增加 `instance?.proxy` 守卫并给 `Query.fields()` 补第二参回调；`share.vue` canvasToTempFilePath `fail` 回调补 `err: any`；`request.ts` 日志内 `res.data?.code` 显式转型 `ApiResponse`。`pnpm type-check` 从 8 错误归零。

## [1.65.0] - 2026-08-19

### Added

- miniapp 分享工坊分享图添加小程序码（98）：三张模板（月度战报/今日日记/技术评分）分享卡底部右下角绘制微信小程序码 `td-qr.png`（真实 PNG 重编码后随包发布，左侧竖排「扫码体验 / Tennis Diary」标签，footer 高度 120→240）。`share.vue` 通过 `node.createImage()` 异步预载二维码后注入管线上下文（`PipelineContext.qrImage`），失败降级为底部留白不阻塞出图并埋点；`footer` 阶段同步 `ctx.drawImage` 保持管线非阻塞。Playwright 新增二维码像素断言，9 张视觉回归快照全量重建。

## [1.64.2] - 2026-08-19

### Fixed

- miniapp 修复 textarea 缺省 140 字上限截断润色文案：微信小程序 `<textarea>` `maxlength` 默认为 140，分享工坊 AI 润色文案（80-150 字 + emoji + 标签）超限被截断；分享页配文、日记表单「今日复盘」、装备表单「使用感受」及 `Field.vue` 组件统一设置 `maxlength="-1"` 不限长度。

## [1.64.1] - 2026-08-19

### Fixed

- miniapp 构建 Circular chunk 警告修复（97）：`stores/auth → services/auth → services/request → stores/auth` 循环分块依赖解耦——`services/request.ts` 移除 `useAuthStore` 静态导入，新增 `onSessionExpired` 回调注册入口，`clearAuth()` 改为清 storage + 通知回调；`stores/auth.ts` 模块顶层注册该回调，401 时延迟调用 `useAuthStore().logout()` 同步重置内存态（行为与之前一致）。网络层保持零 auth-store 依赖，`pnpm build:mp-weixin` 警告消除。

## [1.64.0] - 2026-08-19

### Added

- miniapp 小程序大满贯球场主题（96）：修复「我的」页「青柠主题」开关无实际效果，提供四套球场主题（青柠/澳网/法网/温网）。设计隐喻「网球恒青柠、球场随主题」——`accent`/`accent-dark`/`accent-soft`/`accent-rgb` 恒定青柠（按钮/标签/图表/`confirmColor`/switch），`page-bg`/`card`/`border`/`hero-a`/`hero-b` 按球场取色（背景/卡片/分隔线/深色大卡渐变）。`stores/settings.ts` `ThemePalette` 扩展至 9 Token；新增 `composables/useTheme.ts`（`useThemeStyle()` 返回 `{themeStyle, themeBg}`）；11 页接入 `<page-meta page-style + background-color>`；组件/页面 SCSS 硬编码颜色替换为 CSS 变量（Seg/Stepper/Tag/MoneyToggle/Empty 底色→page-bg，页面级卡片→card，分隔线→border）；mine.vue「球场主题」菜单项 + 主题选择弹层（色块显示球场渐变）。
- miniapp 加强非青柠主题色差（96）：澳网 `#D8E5F4`/`#F0F7FD`、法网 `#E2CABC`/`#F8EDE5`、温网 `#D0E0C9`/`#EDF5E9` 背景/卡片明显区别于青柠；diary/gear hero 卡片背景从固定 `$color-olive` 改为 `var(--color-hero-a/b)` 渐变，与 mine 资料卡/coach hero 卡一致，全端深色大卡随主题。

## [1.63.0] - 2026-08-19

### Added

- server 分享工坊 AI 文案润色（95）：`POST /api/ai/caption` 接收 `template`/`style`/`text`，服务端按当前用户查库（月度战报/今日日记/技术评分）+ 润色 prompt，多风格可选（活泼/简洁/专业），无 Key/异常降级本地模板文案；`generate_caption` 增加 LRU 缓存（MD5 key，20 条上限，永不自动过期，命中打日志），避免重复调用 AI 浪费 token。新增 `ai_service.chat_text` / `build_caption_context` / `build_local_caption` 与 `CaptionRequest`/`CaptionResponse` schema。
- miniapp 分享工坊润色交互（95）：`share.vue` 按钮「重新生成」→「润色文案」、loading「润色中…」、失败 toast「润色失败，已用模板文案」；textarea 内容透传 AI 结合数据润色；风格选择器（活泼/简洁/专业）；空态提前 return（当月无打卡/无日记/无分析）；前端移除所有用户可见的"AI"字眼。
- tests 新增（95）：`test_ai.py` `TestCaption` 润色 prompt/text 透传断言 + `TestCaptionCache` LRU 命中/未命中/淘汰/key 稳定性 5 用例，`test_ai.py` 29 用例。

## [1.62.4] - 2026-08-18

### Fixed

- server Dockerfile slim 镜像系统依赖修复（94）：`modelscope/Dockerfile` + `Dockerfile` 基础镜像从 `python:3.11` 更换为 `python:3.11-slim`（125MB→最终 957MB，节省约 150MB），runtime 阶段添加 `libgl1`（提供 libGL.so.1，MediaPipe TFLite 必需）+ `libglib2.0-0`（提供 libgthread-2.0.so.0，OpenCV 必需）

## [1.62.3] - 2026-08-18

### Fixed

- server Dockerfile 更换基础镜像修复 libGL.so.1 缺失（94）：`modelscope/Dockerfile` + `Dockerfile` 基础镜像从 `python:3.10-slim` 更换为 `python:3.11` 完整版，移除手动系统依赖安装（slim 版本持续缺失图形库：libGL、libEGL、libxcb 等），与本地 Python 3.11.1 版本一致

## [1.62.2] - 2026-08-18

### Fixed

- server Dockerfile 运行时系统依赖修复（94）：`modelscope/Dockerfile` + `Dockerfile` 在 runtime 阶段（非 builder）添加 `libjpeg62-turbo`/`zlib1g`/`libxcb1` 系统依赖，修复多阶段构建中 builder 阶段安装的系统库不会自动继承到 runtime 导致 MediaPipe `libxcb.so.1` 缺失的 503 错误

## [1.62.1] - 2026-08-18

### Fixed

- server 姿态推理日志修复（94）：`pose.py`/`video.py` 异常日志改 f-string + `exc_info=True`，修复异常消息被 LOG_FORMAT 丢弃的问题
- server mediapipe 版本锁定：`pyproject.toml` 锁 `mediapipe==1.0.0`（与 uv.lock 一致），消除本地/容器版本漂移
- server 新增姿态推理真实链路测试：`test_pose_real_inference.py`（4 用例），用真实 JPEG 帧验证完整推理链路

## [1.62.0] - 2026-08-17

### Added

- miniapp 事件埋点补全（59）：补全页面级业务交互埋点（日记/装备/体重/统计/教练/分享）、视频选择与图片保存埋点、静默错误埋点全覆盖，消除无声失败路径；事件日志清单更新至 v1.2
- miniapp 分享工坊保存图片默认名称与微信隐私 API 适配（93）：保存图片使用业务默认名（月度战报/今日日记/技术评分）替代时间戳，隐私弹窗接入微信官方 `wx.getPrivacySetting` API

### Fixed

- miniapp 修复分享图片隐私错误(112)未上报事件
- miniapp 分享图片 footer 整体下移（height 100→120, bottomMargin 100→60）
- miniapp 技术评分进度条行间距继续缩小（itemHeight 210→190→175）

## [1.61.8] - 2026-08-17

### Fixed

- miniapp 通用化隐私/权限错误处理（对齐 tarot 方案）：新增 `privacy.ts` 工具，移除 errno 112 特殊分支和硬编码权限名称引导；运行期权限拒绝 → openSetting，隐私声明问题 → 通用提示；eventLogger 上报失败时 console.warn

## [1.61.7] - 2026-08-16

### Fixed

- miniapp 技术评分进度条行间距缩小（itemHeight 260→220），更紧凑的视觉效果

## [1.61.6] - 2026-08-16

### Fixed

- miniapp 技术评分进度条文字间距优化：标题与进度条间距（barTopOffset 12→35），进度条与评论间距（commentStartOffset 68→80）

## [1.61.5] - 2026-08-16

### Fixed

- miniapp 技术评分进度条行间距增大（itemHeight 195→260），改善视觉层次感

## [1.61.4] - 2026-08-16

### Fixed

- miniapp 技术评分卡片布局优化：整体下移，白色卡片包裹雷达图和进度条区域，总结文本显示在卡片下方；修复summaryStage条件判断（检查analysis.summary而非report.summary）

## [1.61.3] - 2026-08-16

### Fixed

- miniapp 雷达图文字标注优化：标注偏移量从110减小到65更贴近顶点，上下顶点动态居中对齐、左右顶点左右对齐，radarZone高度从420增加到540防止底部标注超出卡片

## [1.61.2] - 2026-08-16

### Changed

- miniapp 分享工坊技术评分三区域分离：将技术评分图片内容区从上到下分为雷达图、进度条、总结三个独立区域，每个区域逐步完善；新增4个Playwright回归测试用例覆盖三个区域

## [1.61.1] - 2026-08-15

### Fixed

- miniapp 去掉用户可见的"AI"字眼：教练主页英雄卡片、分析页进度提示与表单说明、报告页 NTRP 注释、分享卡片标题与文案、页面导航标题，统一改为中性表述（"专属私教"、"教练分析"等）

## [1.61.0] - 2026-08-15

### Added

- admin 静态文件端点移除认证（86）：`/api/admin/system/files/{filename}` 移除 `Depends(get_current_admin)`，解决 `<img>` 浏览器原生请求无法携带 `X-Auth-Token` 导致 401 问题，安全性由文件名不可猜测保证（UUID + 业务前缀）。详见 `docs/plans/86-Admin静态文件端点移除认证.md`
- admin 时间显示统一东八区（87）：新增 `admin/src/utils/date.ts` 共享工具（`formatTs`/`formatIso`/`formatDate` 三个函数，`timeZone: 'Asia/Shanghai'`），8 个视图（admins/analyses/diaries/gears/system/backups/system/event-logs/users/weights）统一导入替代原生 `toLocaleString`；后端备份列表 `created_at` 时间格式添加 `Z` 后缀保证 ISO 8601 合规。详见 `docs/plans/87-Admin时间显示统一东八区.md`

## [1.60.0] - 2026-08-15

### Added

- server 骨骼视频帧率自适应绘制（85）：`video_service.py` 新增 `probe_frame_rate` 函数获取视频帧率（ffprobe 优先，分数格式解析，回退 30fps）；`process_video` 返回 `frame_rate` 字段；`pose.py` `PoseAnalyzeRequest` 新增 `frame_rate` 参数；`pose_service.py` `analyze_frames` 使用 `帧数/时长` 计算骨骼视频帧率，确保播放时长与原视频一致。小程序 `VideoUploadResult` 新增 `frame_rate` 字段，`analyzePose` 新增 `frameRate` 参数，`analyze.vue` 传递帧率参数。详见 `docs/plans/85-骨骼视频帧率自适应绘制.md`

## [1.59.1] - 2026-08-15

### Fixed

- miniapp 视频上传（fix-2026-08-15）：`analyze.vue` 上传前用 `fs.access()` 检查临时文件是否存在，临时文件被系统回收时提示「视频文件已失效，请重新选择」而非 cryptic `uploadFile:fail file not found`（模拟器已知行为，真机无此问题）
- server 骨架视频多帧（84）：`encode_skeleton_video` 改用 `-framerate` + `%04d` 通配符直接读图片序列，修复 ffmpeg concat demuxer 将静态 JPEG 视为无限长流导致输出仅 1 帧的 bug；骨架帧命名同步改为 4 位零填充 `{base}_sk{idx:04d}.jpg`；新增 `TestEncodeSkeletonVideo` 真实 ffmpeg 编码测试

## [1.59.0] - 2026-08-14

### Added

- server 姿态可视化与六边形雷达图（83）：`Analysis.pose` 落库（Alembic 迁移 `c1d2e3f4a5b6`）；`pose_service.py` 新增 `draw_skeleton` / `encode_skeleton_video`（concat + fps + 偶数尺寸 scale，防 x264 奇高报错）/ `analyze_frames` 扩展骨架字段；`POST /api/pose/analyze` 请求体加 `video_url` / `save_skeleton` / `duration`；新建 `app/routers/media.py` 用户端媒体服务（归属校验 + `?token=` 回退鉴权）；`main.py` 注册 media 路由。小程序 `RadarChart.vue` 六边形雷达图（canvas 2d，移植 Web `Charts.tsx:137`）；`analyze.vue` 改为 AI 与姿态并行（`Promise.allSettled`），每次分析都跑姿态并落库；`report.vue` 雷达卡 + 姿态测量卡 + 骨架封面优先 + 原视频/骨架视频切换；`coach.vue` 列表骨架徽标。Admin 详情弹窗新增姿态三角度 + 骨架缩略图/视频。
- tests 新增：`test_pose.py`（draw_skeleton/save_skeleton/video_url 越界）、`test_media.py`（归属/越界/mp4 content-type/query token 鉴权）。

### Fixed

- server 骨架视频编码（83）：x264/yuv420p 对奇数宽高直接报错（实测 `360x269` 返回 rc 187 空输出）；`encode_skeleton_video` 追加 `-vf fps=N,scale=trunc(iw/2)*2:trunc(ih/2)*2` 确保偶数尺寸。

## [1.58.0] - 2026-08-14

### Added

- server 姿态模型下载与随包打包（82）：`server/scripts/download-pose-model.sh` 幂等下载 `pose_landmarker_lite.task`（官方 Google 源，`POSE_MODEL_URL` 可覆盖镜像，sha256 固化 `59929e1d…d574a` + 临时文件 + 大小校验）；双 Dockerfile 按文件 `COPY models/pose_landmarker_lite.task` 随镜像打包（缺失时构建 fail-fast）；`deploy-modelscope.sh` 打包前自动下载 + `FILES_TO_COPY` 加 `models`、`deploy-oci.sh` rsync 前自动下载；`server/models/` 仅 `.gitkeep` 纳入版本管理。详见 `docs/plans/82-姿态模型获取与随包打包.md`
- server MediaPipe 兼容性测试（82）：`TestMediapipeCompat` 断言 mediapipe 1.0 API 路径存在（`python.BaseOptions` / `mp.Image`），防未来版本漂移。

### Fixed

- server 姿态推理真实链路 API 路径（82）：mediapipe 升级 1.0 后 `vision.BaseOptions` / `mediapipe.tasks.python.core.image.Image` / `ImageFormat.SRGB` 路径变更，`pose_service.py` 改用 `python.BaseOptions`、`mediapipe.Image`、`mp.ImageFormat.SRGB`，真实推理端到端返回 33 关键点。

## [1.57.0] - 2026-08-14

### Added

- server AI 模型可用性校验（81）：`POST /api/admin/config/providers/check-models`（权限 `system:config`），两级策略——list（`GET {base_url}/models` 拉可用模型比对）+ probe（不支持 /models 时逐模型 `max_tokens=1` 文本探测，模型名不存在秒回非 200）；解析兼容 `data[]`/`models[]`（id/name/字符串），15s 超时、401/403 鉴权失败、连接/超时镜像 ai-connect 语义；表单值直传无需先保存。详见 `docs/plans/81-AI模型可用性校验与调试脚本.md`
- server 模型调试脚本（81）：`server/scripts/debug-ai.py` 直连生效配置（`get_ai_config` 同源），支持最小探测 / 任意文本对话 / `GET /models` 列表 / 完整六维分析（本地图片 → dataURL 生产同款链路）；`--model/--base-url/--api-key` CLI 覆盖优先；不吞错（非 200 打印真实响应），退出码 0/1。
- admin 服务商表单模型校验（81）：模型列表编辑器每行 ✓ 绿 / ✗ 红徽标 +「校验模型」按钮（`useActionLock` 防重复提交）+ 结果区（list 可用模型列表 / probe 逐模型原因 / 失败 message）。

## [1.56.0] - 2026-08-14

### Added

- server 动态配置系统（78）：配置注册表 7 分类 20 项（`app/core/config_registry.py`）+ `system_configs` 覆盖表，生效值 = DB 覆盖 > env 默认；`GET/PUT/DELETE /api/admin/config`、`POST /api/admin/config/reset`，secret 仅掩码、非法值 400、等于默认值自动删行；AI 三件套（key/base_url/model）可在线编辑；迁移 `da938737d8cb`。详见 `docs/plans/78-动态配置系统与Admin配置页.md`
- admin 系统配置页（78）：分类卡片展示 + 源徽标（默认/内置/自定义）+ 编辑/恢复默认/全部恢复默认；权限 `system:config`。
- server AI 服务商管理（79）：`ai_providers` 表（name 唯一索引 + base_url + api_key + model + enabled）+ `ai.provider` select 配置项（options 动态 = 启用服务商 + custom）；`get_ai_config` 引用解析：选中服务商 → base_url/api_key 直读条目、model 覆盖 > 条目默认，条目禁用/删除自动回落 custom；被引用服务商删除 409、name 重复 400；ai-status 返回 `provider`。迁移 `7e375669cd0d`。详见 `docs/plans/79-AI服务商管理配置直选.md`
- server AI 服务商多模型（80）：`model` → `models` JSON 列表（默认模型 = 首项），新增/编辑/列表均返回 `models` + `default_model`，空列表 400；迁移 `9e8d74e6ab01`（model → models 回填）。详见 `docs/plans/80-AI服务商多模型与模型直选.md`
- admin 服务商管理 UI（79/80）：AI 卡片服务商下拉直选 + 生效配置展示（掩码 key/模型/Base URL）；「管理服务商」弹窗（增删改、api_key 留空保持不变、删除二次确认）；选中服务商后模型二选下拉（写 `ai.model` 覆盖 / 跟随服务商默认清除覆盖）；服务商表单模型列表编辑器（多行增删、首行默认、保存自动去空行）。

## [1.55.1] - 2026-08-13

### Fixed

- server 全局异常处理响应补充 `Access-Control-Allow-Origin` 头：未知异常由最外层 `ServerErrorMiddleware` 生成响应（绕过 `CORSMiddleware`），此前 500 响应缺失 CORS 头导致浏览器误报跨域拦截；现手动补头，便于前端看到真实错误信息。

## [1.55.0] - 2026-08-13

### Added

- miniapp Phase 5 分享工坊：新增 `pages/share/share`（模板选择 + Canvas 2d 卡片预览 + 保存相册 + 文案复制/重新生成）；`utils/shareCanvas.ts` 提供 `drawShareCard`（月度战报 / 今日日记 / 技术评分三模板）与 `genCaption` 文案模板；「我的」页新增「分享工坊」入口。详见 `docs/plans/75-6-Phase5-分享工坊.md`

## [1.54.0] - 2026-08-13

### Added

- miniapp Phase 4 电子教练页：新增 `pages/coach/` 三页（coach 历史列表、analyze 三步分析流、report 完整报告），「我的」页新增「电子教练」入口，`pages.json` 注册。
- miniapp 电子教练数据层：`uploadVideo`（uni.uploadFile 直传 + 抽帧，携带 `X-Auth-Token`）、`analyzeSwing`（AI 六维评分，120s 超时）、`analyzePose`（姿态推理，60s 超时）、`createAnalysis`/`getAnalyses`/`getAnalysis`/`deleteAnalysis`（报告落库与历史回看）；`types` 新增 `VideoUploadResult`/`PoseLandmark`/`PoseResult`，`Analysis`/`AnalysisCreate` 增加 `video_url`。详见 `docs/plans/75-5-Phase4-电子教练小程序页.md`

## [1.53.0] - 2026-08-13

### Added

- server MediaPipe 姿态推理接口 `POST /api/pose/analyze`：CPU 推理逐帧输出 33 关键点（归一化坐标 + visibility）+ 首个可测帧的三角度测量（肘角/膝角/躯干倾角，`measure_angles` 与参考版 `pose.ts` 对齐）；mediapipe 懒加载预检、模型缺失返回 503、无人检测返回 200 + `detected=false`。新增依赖 `mediapipe` 与 `server/models/` 目录（模型文件不纳入版本管理）。详见 `docs/plans/75-3-MediaPipe姿态推理.md`
- server 用户端分析报告落库与历史查询：`POST /api/analyses`（AI 分析成功后落库）、`GET /api/analyses`（历史列表，分页倒序，仅本人）、`GET /api/analyses/{id}`（详情，完整六维报告结构化 JSON）、`DELETE /api/analyses/{id}`；`Analysis` 模型新增 `video_url` 列 + Alembic 增量迁移。详见 `docs/plans/75-4-分析报告落库与历史查询.md`

## [1.52.0] - 2026-08-13

### Added

- admin 分析报告管理增强：详情接口 `GET /api/admin/analyses/{id}` 返回完整六维报告（`report` JSON 对象 + `thumb` 封面 + `highlights` 高光帧数组，非法 JSON 容错返回 `None`）；分析页列表新增「模式」（单次挥拍/综合分析）与「封面」缩略图列，详情弹窗渲染六维评分条/节奏观察/亮点/改进建议/封面与高光帧。详见 `docs/plans/75-B2-Admin同步AI网关功能.md`
- admin AI 网关状态监控：健康检查页新增「AI 网关」卡片，`GET /api/admin/system/ai-status` 探测 AI Key（掩码 `sk-****abcd`，不暴露明文）/ ffmpeg（含 `imageio-ffmpeg` 兜底提示）/ MediaPipe / 姿态模型四项状态并汇总缺失项；`GET /api/admin/system/ai-connect` 由服务端代理 `{AI_BASE_URL}/models` 验证 Key 有效性（不耗 token），失败含状态码反馈
- admin 静态文件服务：新增 `GET /api/admin/system/files/{path}`，`normpath` 路径防护（越界 404）+ 媒体类型映射，供 Admin 渲染 `thumb` / `highlights` 图片；相对路径走静态服务、`http(s)://` 绝对 URL 前端原样直出
- server 新增 `POSE_MODEL_PATH` 配置（MediaPipe 姿态模型路径，默认 `server/models/pose_landmarker_lite.task`）

## [1.51.0] - 2026-08-13

### Added

- server AI 评分代理接口 `POST /api/ai/analyze`：OpenAI 兼容调用阿里云百炼（Key 存服务端，不进入小程序包），六维评分 prompt 与参考版 `analyzeSwing` 对齐，无 Key / 调用失败 / 解析失败自动返回本地降级报告（`build_local_report`，HTTP 200）。详见 `docs/plans/75-1-AI评分代理接口.md`
- server 视频上传与抽帧接口 `POST /api/video/upload`：ffmpeg 抽帧（single 7 / full 8 帧，640px JPEG，`imageio-ffmpeg` 兜底），时长校验（single 15s / full 90s）、采样时间点与参考版 `CoachAnalyze.tsx` 对齐、封面帧提取；新增依赖 `imageio-ffmpeg`。详见 `docs/plans/75-2-视频上传与抽帧.md`

## [1.50.1] - 2026-08-13

### Fixed

- 修复 admin 健康检查界面版本号脱节：`/api/admin/system/health` 的 `version` 由硬编码 `1.0.0` 改为动态读取仓库根 `package.json`（`APP_VERSION`，带生产镜像兜底版本号），此后随 `npm version` bump 自动同步，不再需手动修改。

## [1.50.0] - 2026-08-13

### Added

- admin 日志查看倒序分页优化：后端 `query_logs` 改为尾部 64KB 分块倒序读取（最新优先），新增 `offset` 游标与 `has_more` 标记支持向前翻页加载更早日志；前端日志页新增「刷新」按钮、「加载更早」分页按钮（offset 续载不重叠）、「已加载 N 条」计数，并增加停留最新页时 10s 自动轮询（翻页查看历史不打断）；新增 3 个测试用例（最新优先、offset 分页不重叠、短文件 `has_more=False`）。详见 `docs/plans/74-日志查看倒序分页优化.md`

## [1.49.0] - 2026-08-13

### Added

- server 测试体系引入 `.env.test` 实现环境隔离：`config.py` 新增 `APP_ENV` 环境感知加载（测试环境加载 `.env.test`，`override=True`），`pytest-env` 在 pytest 运行注入 `APP_ENV=test`；测试数据统一落到 `server/data_test/`，不触碰真实 `data/`；`conftest.py` 新增 autouse `_isolate_data_dirs` 将 `DATA_DIR/UPLOAD_DIR/LOG_DIR` 隔离到临时目录、session 级 `_init_test_database` 预建测试库表，清理 `test_system.py` 7 处手工 `monkeypatch` 样板；新增 `.env.test.example`（提交）与 `test_config_env.py` 配置隔离测试，`.gitignore` 忽略 `data_test/` 与 `.env.test`。详见 `docs/plans/73-测试体系引入-env-test实现环境隔离.md`

## [1.48.0] - 2026-08-12

### Added

- admin 备份管理增强：新增独立元数据库 `backup_meta.db`（`backup_records` 记录备份/恢复/上传/删除事件，与业务库隔离、不参与业务备份恢复，纯表驱动列表）；新增上传备份接口（multipart `.tar.gz`/`.db`）、下载备份（`FileResponse`）、删除备份（软删+物理删）；恢复前生成 `pre_restore_*` 完整兜底备份并关联 `restored_from_id`，保证同时只有一个 `restored` 状态；前端新增「上传备份」按钮、「恢复状态」列（已恢复/未使用，关联兜底文件名经 `:title` 悬浮展示）、类型徽标（恢复前兜底/上传）、下载/删除按钮。详见 `docs/plans/72-Admin-备份管理增强.md`

## [1.47.1] - 2026-08-11

### Fixed

- 修复魔搭创空间数据持久化失效：`server/modelscope/Dockerfile` 的 `DATA_DIR` 从非持久化的 `/data` 改为魔搭持久化卷 `/mnt/workspace`，容器重启后 SQLite 数据库、上传文件与日志不再丢失（转移/重命名创空间除外）。同步更新 `modelscope/README.md` 与 `docs/plans/65-*.md`。

## [1.47.0] - 2026-08-11

### Added

- admin 新增 Cloudflare Workers 部署方式：生产构建 `base` 从硬编码 `/admin/` 改为默认 `/`（读取 `BUILD_BASE`），Nginx 特例用 `pnpm build:nginx`（`BUILD_BASE=/admin/`）保持 `/admin/` 前缀；新增 `admin/worker/index.ts`（纯 Workers 入口，`ASSETS` 绑定伺服 `dist/`，SPA history fallback + 静态长缓存）与 `admin/wrangler.toml`；Dockerfile 改用 `build:nginx`；新增 `.github/workflows/deploy-admin-workers.yml`（wrangler-action 自动部署）。详见 `docs/plans/71-Admin-Cloudflare-Workers-部署.md`

## [1.46.0] - 2026-08-11

### Added

- admin 日记/装备/体重管理页新增点击行查看详情：公共 `Table` 组件增加可选 `rowClickable` prop（向后兼容，默认关闭）与 `row-click` 事件，actions 列 `@click.stop` 阻止删除误触发行点击；三个页面接入事件日志风格的自定义大弹窗（`max-w-2xl`、两列网格、遮罩/右上角/底部三处关闭），日记 JSON 字段（costs/gears）解析格式化展示。详见 `docs/plans/70-Admin-日记装备体重点击查看.md`
- 后端补齐体重单条查询接口 `GET /api/admin/weights/{id}`（与日记/装备对齐），前端 `weights.ts` 新增 `getWeight`

## [1.45.1] - 2026-08-11

### Fixed

- 修复 miniapp「我的」页「编辑资料」重复跳转（打开两次）：用户信息卡整体绑定的 `@tap` 与卡内底部「编辑资料」按钮事件冒泡叠加导致 `navigateTo` 触发两次。移除整卡点击，跳转收敛到卡片右侧 `›` 箭头与底部按钮（`@tap.stop` 阻止冒泡）。详见 `docs/plans/31-Phase2-5-我的页.md`

## [1.45.0] - 2026-08-11

### Added

- miniapp 新增全局 Loading 遮罩：`request.ts` 以请求计数器控制 loading 开关（并发请求不提前消失），新增 `useAppStore` 与 `Loading.vue` 全屏遮罩组件并在 `App.vue` 挂载。详见 `docs/plans/69-miniapp全局Loading遮罩.md`

## [1.44.0] - 2026-08-11

### Added

- admin 新增全局 Loading 遮罩：axios 拦截器以请求计数器控制，所有 API 请求自动显示加载反馈；新增 `useActionLock` 组合式函数，列表页提交类操作（保存/重置密码/状态切换/删除）防重复提交并补充成功 toast 提示。详见 `docs/plans/68-Admin全局Loading与防重复提交.md`

### Fixed

- admin 事件日志表格布局优化：移除"页面"列、表头防换行（`whitespace-nowrap`）、表格容器支持横向滚动（`overflow-x-auto`）、列宽与内边距对齐公共 `Table` 组件，避免表格过宽挤压侧边栏

## [1.43.4] - 2026-08-11

### Fixed

- 修复 admin 用户管理与事件日志详情中头像 URL 未拼接后台地址：`users/index.vue` 的 `getAvatarUrl` 与 `system/event-logs.vue` 的 `resolveAvatarUrl` 重新引入 `VITE_API_BASE_URL` 前缀，生产环境（管理端与后台不同域名）头像不再 404

## [1.43.3] - 2026-08-10

### Fixed

- 修复表单保存按钮可连点导致重复提交，新增 `saving` 锁防止并发请求

## [1.43.2] - 2026-08-10

### Fixed

- 修复 form 页面（日记/装备）在页面栈底时 `navigateBack` 抛错，改用 `safeNavigateBack` 自动回退到 tabBar

## [1.43.1] - 2026-08-10

### Fixed

- 修复 `eventLogger.ts` 中 `require("@/stores/auth")` 在小程序环境别名解析失败，导致模块未定义错误

## [1.43.0] - 2026-08-10

### Added

- 新增 Cloudflare Workers 反向代理（`proxy/` 目录），解决魔搭 `.ms.show` 网关 CORS 预检不返回 `X-Auth-Token` 导致 admin 前端跨域问题
- Worker 支持 OPTIONS 预检返回自定义 CORS 头 + 服务端转发透传 `X-Auth-Token`
- 新增方案文档 `docs/plans/67-Cloudflare-Workers-代理-ModelScope-方案.md`
- 新增 `proxy/README.md`，含快速开始、部署命令与前端接入说明
- `proxy/` 加入 pnpm workspace

## [1.42.3] - 2026-08-10

### Fixed

- 修复魔搭创空间鉴权头被网关占用导致登录后 `/me` 401：后端 `auth.py` 以 `APIKeyHeader` 统一读取自定义头 `X-Auth-Token`，移除 `Authorization` 回退与 `Request` 注入
- admin 前端 `api/index.ts` 请求头改用 `X-Auth-Token`
- miniapp 三处（`request.ts` / `auth.ts` / `eventLogger.ts`）请求头改用 `X-Auth-Token`
- 后端测试 `test_auth.py` / `admin/conftest.py` 同步改用 `X-Auth-Token`
- 诊断脚本 `diag-admin-auth.sh` 改用 `X-Auth-Token`，判断依据同步更新
- 新增方案文档 `docs/plans/66-ModelScope部署鉴权头兼容改造.md`

## [1.42.2] - 2026-08-10

### Fixed

- 修复魔搭创空间 `.ms.show` 公网访问被网关拦截返回 `10011402001`：部署脚本 `deploy-modelscope.sh` 新增 `MODEL_SCOPE_VISIBILITY` 变量（默认 `false`=公开体验），创建创空间时不再写死 `private: true`
- `.env.modelscope.example` 补充创空间可见性配置说明（`true`=私密 / `false`=公开体验）

## [1.42.1] - 2026-08-10

### Changed

- 魔搭构建加速：新增 `server/modelscope/Dockerfile` 专属镜像，apt 源替换为 `mirrors.aliyun.com`、pip/uv 索引指向阿里云 PyPI，解决跨境网络导致的构建慢问题
- `deploy-modelscope.sh` 优先复制魔搭专用 Dockerfile（含阿里云源加速），无则回退根目录通用版

### Fixed

- 修复魔搭创空间 Docker 构建失败：`server/.gitignore` 忽略 `uv.lock` 导致 GitHub Actions checkout 后缺文件，`Dockerfile` 的 `COPY pyproject.toml uv.lock ./` 在 COPY 阶段直接报错
- 将 `server/uv.lock` 纳入版本管理，保证本地 / CI / 魔搭三方依赖一致
- 部署脚本 `deploy-modelscope.sh` 在 `git add -A` 后补 `git add -f uv.lock pyproject.toml` 兜底，防止再次因忽略规则漏包

## [1.42.0] - 2026-08-09

### Added

- 新增 Server 部署方案（魔搭创空间 ModelScope Studio Docker 免费托管）：
  - 创建 `docs/plans/65-Server部署方案-ModelScope-创空间.md`（方案文档）
  - 创建 `server/modelscope/ms_deploy.json`（docker sdk / CPU 免费档 / 7860 端口）
  - 创建 `server/modelscope/README.md`（建仓、Secrets、反代、验证完整指南）
  - 创建 `server/scripts/deploy-modelscope.sh`（打包 + API Secrets + git push + 健康检查）
  - 创建 `server/.env.modelscope.example`（魔搭部署配置模板）
  - 创建 `.github/workflows/deploy-server-modelscope.yml`（push server/** 自动部署）
- 复用既有 Dockerfile（监听 7860），敏感环境变量通过魔搭 Secrets API 注入，不推送 git

## [1.41.1] - 2026-08-09

### Added

- 新增 Server 部署方案（Oracle Cloud Always Free 免费 VM）：
  - 创建 `docs/plans/64-Server部署方案-Oracle-Cloud.md`（方案文档）
  - 创建 `server/oci/README.md`（建机、安全组、Block Volume、初始化、部署完整指南）
  - 创建 `server/scripts/oci-bootstrap.sh`（VM 初始化：Docker/Compose/UFW/可选 Nginx+Let's Encrypt）
  - 创建 `server/scripts/deploy-oci.sh`（rsync 同步代码 + 远端 docker compose 重建 + 健康检查）
  - 创建 `server/.env.oci.example`（OCI SSH 配置模板）
  - 创建 `.github/workflows/deploy-server-oci.yml`（push server/** 自动部署到 OCI VM）
- 部署脚本支持 SSH 私钥「路径 / 内容」两种形式，CI 直接传私钥内容到临时文件
- 远端 .env 自动生成（JWT/WX/管理员凭据），敏感信息不推送到代码仓库

## [1.41.0] - 2026-08-09

### Added

- 新增 Server 部署方案（Docker + HF Space）：
  - 创建多阶段 Dockerfile（builder + runtime，镜像体积约 300MB）
  - 创建 docker-compose.yml（含数据卷持久化，默认端口 8000）
  - 创建 .dockerignore（排除 .venv、tests、__pycache__ 等）
  - 创建 docker-entrypoint.sh（启动时自动执行 alembic upgrade head）
  - 创建 .github/workflows/deploy-server-hf.yml（GitHub Actions 自动部署）
  - 创建 server/scripts/deploy-hf.sh（HF Space 部署脚本）
  - 创建 server/.env.hf.example（HF Space 环境变量模板）
  - 创建 server/spaces/README.md（HF Space 部署完整指南）
  - 创建 docs/plans/63-Server部署方案-Docker与HF-Space.md（方案文档）
- 部署脚本通过 HF API 设置 Secrets，敏感信息不推送到 git repo
- 环境变量校验：检测 GitHub Actions 环境，校验必需 Secrets 是否配置
- JWT_SECRET 生成命令文档（python/openssl 两种方式）

## [1.40.5] - 2026-08-09

### Fixed

- 修复 Admin 端 API 直连问题：移除代理配置，生产构建使用相对路径直连后台
- 修复 Admin 端支持生产环境子路径部署，login 路由使用 `VITE_ADMIN_BASE` 环境变量
- 修复 Admin 端 `VITE_API_BASE_URL` 环境变量配置，dev 模式通过 proxy 转发，生产模式直连

## [1.40.4] - 2026-08-09

### Fixed

- 修复事件日志 trace_id 不一致问题：登录、体重、装备、日记的原子操作（开始→成功/失败）现在使用同一个 trace_id，便于链路追踪

## [1.40.3] - 2026-08-09

### Fixed

- 修复 LineChart 组件使用 `getCurrentInstance().proxy` 替代 `this`，解决 Canvas 节点查询失败的问题

## [1.40.2] - 2026-08-09

### Fixed

- 修复 LineChart 组件在小程序中 SVG 路径数据未正确渲染的问题（改回 Canvas 2D 并使用 `this` 上下文）

## [1.40.1] - 2026-08-09

### Fixed

- 修复 LineChart 组件 X 轴标签 `wx:else` 编译错误（改用 `<template>` 包裹）

## [1.40.0] - 2026-08-09

### Changed

- LineChart 组件从 Canvas 2D 迁移到 SVG，解决小程序自定义组件中节点获取失败的问题

## [1.39.4] - 2026-08-09

### Fixed

- 修复统计页面体重趋势折线图不显示的问题（改用 setTimeout 确保 canvas 节点完全挂载）

## [1.39.3] - 2026-08-09

### Fixed

- 修复统计页面体重趋势折线图不显示的问题（使用双重 nextTick 确保 canvas 节点就绪）

## [1.39.2] - 2026-08-09

### Fixed

- 移除「我的」页面重复的编辑资料入口

## [1.39.1] - 2026-08-09

### Fixed

- 修复 LineChart 组件使用 `getCurrentInstance()` 在小程序环境中返回 null 导致 `$scope` 报错的问题

## [1.39.0] - 2026-08-09

### Added

- 事件日志新增 `trace_id` 和 `action` 独立字段，`extra` 只保留业务 payload
- 业务动作类型统一为 `business`，网络错误为 `network`，崩溃为 `crash`
- 管理端事件日志新增 `action` 搜索框和表格列
- 事件日志支持按 `trace_id` 和 `action` 精确过滤
- 小程序业务动作埋点覆盖：登录、资料更新、日记 CRUD、装备 CRUD、体重 CRUD
- 埋点携带精确操作时间 `client_time`（毫秒时间戳）和唯一操作链路 ID `trace_id`

### Fixed

- 修复头像上传后响应解析失败导致头像不更新的问题
- 修复编辑日记/装备时因 `editingId` 非响应式导致保存变成新增的问题
- 修复 form.vue 中 `ref` 未导入导致编译错误
- 修复 Admin 端日记/装备/体重创建时间显示 1970 年问题（时间戳类型不匹配）
- 修复 Admin 端创建时间显示精度，改为显示时分秒
- 修复日记/装备/体重列表排序问题：按创建时间倒序排列（原按 date/id）
- 修复事件日志上报时 dict 类型无法存入 SQLite Text 列的报错
- 修复事件日志响应序列化错误（extra/device_info 需 JSON 解析，created_at 需转 float）

## [1.38.0] - 2026-08-08

### Added

- 新增 Admin 前端 toast 提示组件（`stores/toast.ts` + `components/common/Toast.vue`），支持 success/error/warning/info 四种类型
- API 拦截器自动显示错误提示：业务错误 code!==0、HTTP 401/403/404/500 均自动弹出 toast
- 优化用户详情模态框布局：头像居中、信息卡片式展示、OpenID 脱敏、性别/时间格式化
- 新增 Admin 前端 `posts.ts` 和 `checkins.ts` API 模块

### Fixed

- 修复 Admin 前端 API 类型定义与后端 schema 不匹配问题：`feelings`→`feeling`、`photos`→`photo`、`body_fat`→`bust/waist/hip`、`type`→`kind`、`report`→`summary`
- 修复用户头像相对路径问题：`avatars/` → `avatar/`，拼接完整 URL
- 修复角色管理按钮不可点击问题：移除前端 `disabled` 限制，由后端保护系统角色
- 修复角色弹窗未重置问题：新建/编辑/关闭时清空表单

### Changed

- 更新文档状态与实际进度对齐（README/AGENTS/docs/plans）
- 精简 AGENTS.md（387行→114行）

## [1.37.0] - 2026-08-08

### Added

- 实现系统运行时长显示：`/api/admin/system/health` 接口的 `uptime` 字段从 "unknown" 改为真实运行时长，格式化为 "X天X小时X分钟X秒"

### Fixed

- 修复系统健康检查数据库连通性检测报错：`db.execute("SELECT 1")` 改为 `db.execute(text("SELECT 1"))`，适配 SQLAlchemy 2.0+

## [1.36.0] - 2026-08-08

### Added

- 统一后台API响应格式：所有接口返回 `{code, message, success, data}` 四字段
  - 新增 `schemas/common.py` 定义 `ApiResponse<T>`、`PaginatedData<T>`、`ErrorCode`
  - 注册全局异常处理器（HTTPException/ValidationError/Exception），自动转换为统一格式
  - 改造用户端路由（auth/diaries/gears/weights/checkin/stats/upload）
  - 改造 Admin 路由（auth/users/diaries/gears/weights/checkins/analyses/posts/roles/admins/system）
  - Admin 前端拦截器判断 `code===0` 返回 data，否则 reject
  - Miniapp 前端拦截器判断 `code===0` 返回 data，否则显示 toast

### Changed

- 错误码规范：0=成功，10000-19999=认证授权，20000-29999=参数校验，30000-39999=业务逻辑，50000-59999=服务器内部错误

## [1.35.0] - 2026-08-08

### Added

- 新增后台管理前端（Phase Admin 全部完成）：
  - 项目初始化（Vite + Vue 3 + TypeScript + Tailwind CSS）
  - 实现主布局（侧边栏、头部、面包屑）
  - 实现登录页（账号密码登录）
  - 实现仪表盘（数据概览卡片、系统状态）
  - 实现用户管理页面（列表、查看、删除）
  - 实现角色管理页面（列表、新建、编辑、删除、权限配置）
  - 实现管理员管理页面（列表、新建、编辑、重置密码、启用/禁用、删除）
  - 实现日记管理页面（列表、删除）
  - 实现装备管理页面（列表、删除）
  - 实现体重管理页面（列表、删除）
  - 实现分析报告页面（列表、查看、删除）
  - 实现系统监控（健康检查、日志查看、备份管理）
  - 通用组件（Table、Pagination、Modal、StatCard）
  - 配置 Nginx 和 Docker 部署

## [1.34.0] - 2026-08-08

### Added

- 新增系统监控管理API与日志分离（Phase B2-3）：
  - 新增日志分离功能（admin.log/user.log/app.log）
  - 支持结构化JSON日志输出
  - 新增请求日志中间件（自动识别admin/user请求）
  - 实现系统健康检查增强接口（数据库连通性/磁盘使用/运行时长）
  - 实现运行时指标接口（各表数据量/数据库大小）
  - 实现日志查询接口（按文件/级别/关键字过滤）
  - 实现数据库备份接口（SQLite在线备份）
  - 实现备份列表接口
  - 实现数据恢复接口（含自动备份当前库）
  - 完成测试用例（6 个测试全部通过）

## [1.33.0] - 2026-08-08

### Added

- 新增数据查看管理API（Phase B2-2）：
  - 实现用户管理接口（列表/详情/删除），支持分页
  - 实现日记管理接口（列表/详情/删除），支持分页和用户筛选
  - 实现装备管理接口（列表/详情/删除），支持分页和用户筛选
  - 实现体重管理接口（列表/删除），支持分页和用户筛选
  - 实现打卡管理接口（列表/删除），支持分页和用户筛选
  - 实现分析管理接口（列表/详情/删除），支持分页和用户筛选
  - 实现发布管理接口（列表/详情/删除），支持分页和用户筛选
  - 新增分页响应模型（`PaginatedResponse`）
  - 新增管理端响应模型（用户/日记/装备/体重/打卡/分析/发布）
  - 完成测试用例（4 个测试全部通过）

## [1.32.0] - 2026-08-08

### Added

- 新增角色权限系统与管理员管理功能（Phase B2-1）：
  - 新增 `Role` 模型与 `Admin` 模型（含 `role_id` 外键关联）
  - 实现权限常量定义（`permissions.py`），包含用户/数据/系统/管理员/角色管理共 30+ 权限
  - 实现初始角色数据初始化（超级管理员/普通管理员/只读管理员）
  - 实现管理员认证（登录/获取信息/修改密码），使用独立 JWT 密钥
  - 实现角色管理接口（CRUD + 权限列表）
  - 实现管理员管理接口（列表/创建/编辑/重置密码/启用禁用/删除）
  - 新增权限校验依赖（`require_permission`），支持细粒度权限控制
  - 新增 Alembic 迁移脚本（`add roles and admins tables`）
  - 完成测试用例（14 个测试全部通过）

## [1.31.3] - 2026-08-08

### Fixed

- 修复头像显示 401 Unauthorized：`GET /api/upload/avatar/{user_id}/{filename}` 原先要求 JWT 鉴权，但微信 `<image>` 组件无法携带 Authorization header，导致每次展示头像都触发 401。移除该 GET 端点的 `Depends(get_current_user)`，改为公开访问（URL 含 user_id + UUID 文件名，不可猜测，安全性足够）

## [1.31.2] - 2026-08-08

### Fixed

- 修复小程序登录失败时 toast 误弹无意义 "request:ok"：`services/request.ts` 的 `parseDetail` 去掉 `res.errMsg` 兜底（`uni.request` success 回调中 `errMsg` 恒为 "request:ok"，与 HTTP 状态码无关），改为优先取后端 `detail`/`message` → 非 JSON 文本 → 基于状态码的 `请求失败（HTTP 4xx/5xx）` 通用提示（见方案 41）
- 修复登录接口 401 误触发登出引导：`services/auth.ts` 的 `login()` 传 `handle401: false`，登录失败（如 code 过期）不再弹「请到『我的』页登录后使用」，由调用方直接展示真实错误（见方案 41）
- 修复登录成功后「我的」页昵称误显「未登录」：新注册用户后端 `nickname` 默认为空串，`mine.vue` 旧逻辑 `nickname || "未登录"` 兜底误判；改为新增 `profileName` computed，未登录显示「未登录」、已登录昵称为空显示「微信用户」（见方案 42）

## [1.31.0] - 2026-08-07

### Added

- 我的页与资料详情页 tarot 化改造（见方案 40）：`mine.vue` 用户卡升级为深橄榄渐变 + 青柠光斑，登录后展示累计打球/时长/装备三列统计徽章（`getStats`，失败静默降级 0），功能入口改为「图标 + 标签 + 箭头/开关」卡片式菜单（统计总览 `switchTab` / 编辑资料 / 金额隐私 / 青柠主题），退出登录移除并移入资料详情页，未登录隐藏功能菜单仅保留「微信一键登录」唯一入口且不发 `/stats` 请求；`profile-edit.vue` 居中大头像（小程序 `chooseAvatar` + H5 `chooseImage` 降级）、细分隔线表单、每字段自动保存（昵称 `blur/confirm`、性别/生日 `picker change`，成功轻提示）、底部独立「退出登录」确认后回「我的」Tab

## [1.30.1] - 2026-08-07

### Fixed

- 修复全项目 Tailwind 自定义色未生成导致界面无品牌色：`vite.config.ts` 中 `cssEntries` 原指向 `src/App.vue`（Vue 组件），weapp-tailwindcss 解析不到其 scss 内的 `@tailwind` 指令，回退默认 config，`bg-olive`/`from-olive`/`via-olive-mid` 等自定义色类未生成到 WXSS，所有页面纯白无层次。改为新建独立 `src/app.css`（含 `@config "../tailwind.config.js"` 显式指定 config 路径 + `@tailwind base/components/utilities`）、`App.vue` 非 scoped `@import '@/app.css'`、`cssEntries`/`tailwindcssBasedir` 修正（对齐 tarot 集成方式），全项目 olive/lime/paper 品牌色类恢复（见方案 40）

## [1.30.0] - 2026-08-07

### Added

- 后端接入 Alembic 数据库迁移（见方案 39）：新增 `alembic.ini` 与 `alembic/` 骨架，`env.py` 复用应用配置 `DATABASE_URL` 与 `Base.metadata`；生成基线迁移 `3a79ce8c1f19_initial_schema.py`（全部 7 张表 + `users.gender/birthday`）；`app/models/__init__.py` 集中导出全部模型；`pyproject.toml` 新增 `alembic` 依赖并对 `alembic/versions/*` 配置 ruff `per-file-ignore` 与 `format exclude`；新增 `test_models_registry.py` 校验模型注册与元数据完整性。此后模型字段变更一律走 `alembic revision --autogenerate` + `upgrade head`，严禁手工 `create_all`

## [1.29.0] - 2026-08-07

### Added

- 用户资料编辑与登录时序修复（参考 tarot，见方案 38）：`/api/auth/login` 一次返回 `{ access_token, user, is_new }`（修复「一键登录返回 token 后仍提示请先登录」的未登录短路 bug），新增 `PUT /api/auth/me` 更新用户资料（昵称/头像/性别/生日，仅更新传入字段）与 `POST /api/upload/avatar` 头像上传，`users` 表新增 `gender`/`birthday` 列；前端新增「编辑资料」页（`profile-edit`），「我的」页用户卡可点击进入并展示脱敏 ID/性别/生日，新增 `updateProfile`/`uploadAvatar`/`resolveUploadUrl`/`maskMiddle` 等工具与对应测试

## [1.28.3] - 2026-08-07

### Fixed

- 修复后端微信登录报 `appid missing (41002)`：`server/app/core/config.py` 中 `load_dotenv` 的路径 `Path(__file__).resolve().parent.parent / ".env"` 少算一级 `.parent`（`config.py` 位于 `app/core/` 下，实际加载到不存在的 `server/app/.env`），导致 `WX_APPID`/`WX_SECRET` 始终为空、微信 `code2session` 收到空 `appid` 而返回 `41002`。修正为 `.parent.parent.parent` 指向 `server/.env`，登录鉴权恢复可用（见方案 37）

## [1.28.2] - 2026-08-07

### Fixed

- 修复日记/装备/统计 Tab 页面空白且无空态：业务页通过 `@/components` **桶导出**引入自定义组件时，uni-app mp-weixin 编译器无法将其注册进 `usingComponents`，编译产物各页面 `usingComponents` 为空，但 WXML 又引用了 `<empty>`/`<line-chart>`/`<popup>` 等未注册组件导致渲染为空白。将 `diary.vue`/`gear.vue`/`stats.vue`/`diary/form.vue`/`gear/form.vue` 五处组件引入改为**直接文件导入**（`@/components/xxx.vue`），重建后各页面 `usingComponents` 正确注册（见方案 36）

## [1.28.1] - 2026-08-07

### Fixed

- 修复 `src/utils/jwt.ts` 在微信小程序编译不兼容导致运行时 `module 'utils/jwt.js' is not defined`：重写 base64 解码实现，移除 `String.fromCharCode(...bytes)` 展开 `Uint8Array` 及 `atob` + `decodeURIComponent` 组合等高阶语法，改为循环逐字节解码 + 独立 UTF-8 解码函数，规避微信开发者工具 es6 二次编译解析失败而静默跳过注册该模块的问题

## [1.28.0] - 2026-08-07

### Added

- 引入游客模式（参考 tarot 项目）：登录态改为基于「token 有效（存在且未过期）」判断（新增 `src/utils/jwt.ts` 解析 JWT 的 `exp`），新增 `auth.isGuest` 游客态 getter；`App.vue` `onLaunch` 移除无条件静默登录，未登录即保持游客态、不再自动请求后台；日记/装备/统计页在游客态不发请求并展示 `Empty` 游客引导空态（「去登录」跳转「我的」页），`request.ts` 本地短路继续作为兜底（见方案 35）

## [1.27.0] - 2026-08-07

### Added

- 统计页「数据总览」增加空数据处理：新增 `statsLoading` 加载状态（避免加载中误显示空态）、`hasAnyData` 计算属性判断是否有统计数据，完全无数据时显示 `Empty` 空态引导并可跳转日记页记录（见方案 34）

## [1.26.0] - 2026-08-07

### Added

- 未登录友好提示：`request.ts` 网络层加未登录硬门控（`auth=true` 且无本地 token 时直接短路不发请求，3s 节流 toast 引导「请到『我的』页登录后使用」，401 统一引导）；三个数据 store（weight/diary/gear）`fetchList` 加 try/catch 吞错并 `console.error` 打印，`stats.vue` `getStats` 的 catch 补日志，消除未登录/请求失败时的未捕获 `MiniProgramError`（见方案 33）

## [1.25.0] - 2026-08-07

### Added

- Tailwind 小程序适配方案迁移：弃用 `tailwindcss-miniprogram-preset`，改用 `weapp-tailwindcss@^5`（Vite 插件，命名导出 `WeappTailwindcss`），配置 `rem2rpx` 单位转换 + 类名混淆，`tailwind.config.js` 去 preset 并加 `corePlugins.preflight: false`，PostCSS 插件配置抽到独立 `postcss.config.js`，`App.vue` 改用 `@tailwind utilities;`，根治 WXSS 对 `skewY`/`scaleY` 编译错误（见方案 32）

## [1.24.0] - 2026-08-06

### Added

- Phase 2 我的页：用户信息展示 + 手动登录/登出 + 设置入口（金额隐私开关、主题偏好），对接 `/api/auth/me`，见方案 31
- Phase 2 统计页：汇总卡片（累计打球/时长/平均强度/心情/总花费/装备数，对接 `/api/stats`）+ 体重管理（记录/历史/趋势折线图，对接 `/api/weights`），见方案 30
- 新增 `LineChart` canvas 折线图组件（`src/components/LineChart.vue`）
- Phase 2 装备页：画报卡片流 + 种类筛选 + 新增/编辑表单页 + 照片上传，对接 `/api/gears`，见方案 29
- `utils` 新增 `choosePhoto` 图片压缩工具（`uni.chooseMedia` + canvas 压缩），`services/data` 补充 `getGear` 详情接口
- Phase 2 日记页：日记列表页 + 新建/编辑表单页，对接 `/api/diaries`，见方案 28
- 新增 `Seg` / `EmojiScale` 表单组件
- 建立组件库地基：`Empty` / `NavBar` / `Cell` / `Field` / `Stepper` / `Tag` / `ActionSheet` / `Popup`（`src/components/`），见方案 27
- 迁移前端 `utils` 工具函数（枚举 / 日期 / 金额 / 聚合）
- 数据层 `services/data.ts` 封装全部接口 + 三个数据 store（diary/gear/weight）对接真实接口，见方案 27
- 静默登录门控：`auth` store 新增「曾登录」标志（storage 键 `td_has_logged_in`），`ensureLogin()` 仅在已持有 token 或曾登录过时才触发 `wx.login` → 后端登录链路，首次启动（从未登录）不再请求后台，等待用户手动登录；`logout()` 清除该标志，登出后不再自动登录（见方案 25）

## [1.23.1] - 2026-08-06

### Fixed

- 修复小程序 `app.wxss` 编译失败：`diary.vue` 的 Tailwind 冒号变体类 `active:opacity-90` 编译出 `.active\:opacity-90:active` 反斜杠转义选择器，WXSS 解析器不支持而报 `unexpected '\'` 错误；改为自定义类 `press-btn` + scoped `.press-btn:active`，并沉淀约束「小程序端禁用 Tailwind 冒号变体」
- 修复小程序静默登录 404：端口 8000 被另一项目（Tennis Motion System）占用，后端请求打到错误服务器；结束占用进程并启动 Tennis Diary 后端，`/api/auth/login` 恢复正常路由（见方案 24）

## [1.23.0] - 2026-08-06

### Added

- 前端构建期注入微信小程序配置（参照 shadaileng/tarot）：新增非 `VITE_` 前缀环境变量 `TD_APPID`（微信 AppID）与 `TD_URL_CHECK`（域名白名单校验开关），由 `vite.config.ts` 内联插件在 `closeBundle` 时写入构建产物 `dist/*/mp-weixin/project.config.json` 的 `appid` 与 `setting.urlCheck`，不改动 `src/manifest.json`、不进入打包产物；`miniapp/.gitignore` 补齐 `.env.*` 忽略（仅保留 `.env.example`），新增 devDependency `@types/node`

## [1.22.0] - 2026-08-05

### Added

- 前后端引入 `.env` 配置模板：前端 `config/index.ts` 改为读 `VITE_API_BASE_URL` / `VITE_REQUEST_TIMEOUT`（`import.meta.env`），未配置时按平台兜底；后台新增 `python-dotenv` 以绝对路径自动加载 `server/.env`；新增 `miniapp/.env.example` 与 `server/.env.example` 模板（仅模板提交，实际 `.env.*` 由各环境手动配置）
- 前端 storage 键名统一收口到 `src/constants/storage.ts`（`STORAGE_KEYS`），`request.ts` / `auth.ts` / `settings.ts` 均引用常量，消除 `td_*` 魔法字符串散落

## [1.21.0] - 2026-08-05

### Added

- 小程序端对接 B1 微信登录流程：`services/auth.ts` 封装 `getLoginCode()`（`uni.login` 取 code，小程序编译为 `wx.login`），`auth` store 的 `login()` 完成「取 code → 换 JWT → 取用户 → 持久化」链路，新增 `ensureLogin()` 静默登录（无 token 时 App.onLaunch 自动触发），登录失败提示并保持未登录态（Phase 1 小程序前端基础能力全部完成）

## [1.20.0] - 2026-08-05

### Added

- 小程序端封装网络层：`config/index.ts` 按平台区分 baseURL（小程序 `127.0.0.1` / H5 `localhost`），`services/request.ts` 封装 Promise 化 `get/post/put/delete` 并自动注入 JWT、统一 `ApiError` 与 401 处理，`services/auth.ts` 提供登录/获取用户 API，`auth` store 的 `login()` 对接网络层，`App.vue onLaunch` 恢复登录态与偏好

## [1.19.0] - 2026-08-05

### Added

- 小程序端搭建 Pinia 全局状态（`src/stores/`）：`auth`（token/用户登录态 + 持久化）、`diary`/`gear`/`weight`（数据列表，网络 action 待 Phase1-7 填充）、`settings`（金额隐私/主题偏好 + 持久化），并在 `main.ts` 注册 `createPinia()`

## [1.18.0] - 2026-08-05

### Added

- 小程序端完成 `types.ts` 类型定义迁移（`src/types/index.ts`）：字段命名对齐后台 B1 Pydantic Schemas（`created_at`/`buy_date`/`course_id` 等蛇形命名），区分主实体接口（含 `id`/`created_at`）与创建/更新入参（`*Create`/`*Update`），`RallyClip.video` 改用 `File`（小程序 `uni.chooseMedia`），补充后台交互类型 `User`/`Token`/`LoginRequest`/`Stats`/`MessageResponse`，保留 `Course`/`AISettings` 等前端本地类型

## [1.17.0] - 2026-08-05

### Changed

- 小程序 UI 组件方案变更：移除 `@vant/weapp`（原生组件无法被 Vite/Vue 编译，复制 `wxcomponents/` 与「构建 npm」两种引入方式均有硬伤），改用 Tailwind CSS 自定义组件；删除 `src/wxcomponents/`（约 500 个文件）、清理 `pages.json` usingComponents 与 `App.vue` 的 `--van-*` 变量，`diary.vue` 占位页改用 Tailwind 实现 Tab/Cell/按钮

## [1.16.0] - 2026-08-05

### Added

- 小程序建立标准目录结构（components/stores/types/utils/services/styles），配置四 Tab 底部 TabBar（日记/装备/统计/我的），生成橄榄绿/青柠主题占位图标并移除模板默认页

## [1.15.0] - 2026-08-05

### Added

- 初始化 uni-app（Vue3 + Vite + TS）小程序前端工程 `miniapp/`，接入 pnpm 工作区，`build:mp-weixin` / `dev:mp-weixin` / `type-check` 均通过

## [1.14.0] - 2026-08-05

### Added

- 实现文件下载接口（`GET /api/files/{filename}`）：按相对 `UPLOAD_DIR` 路径下载文件，含路径穿越防护、用户归属校验（仅可下载本人 Gear 引用的文件）、按扩展名推断 Content-Type

## [1.13.0] - 2026-08-05

### Added

- 实现统计汇总接口（`GET /api/stats`）：聚合当前用户的日记、装备、分析数据，返回训练次数/总时长/平均强度与心情/总花费/装备数/分析数与平均分

## [1.12.0] - 2026-08-05

### Added

- 实现打卡接口（`/api/checkin`）：训练营打卡查询 / 签到，同用户+同课程+同日期幂等，强制用户归属校验

## [1.11.0] - 2026-08-05

### Added

- 实现体重记录接口（`/api/weights`）：列表 / 添加 / 删除，强制用户归属校验

## [1.10.0] - 2026-08-05

### Added

- 实现装备 CRUD 接口（`/api/gears`）：列表 / 添加 / 详情 / 编辑 / 删除，强制用户归属校验

## [1.9.0] - 2026-08-05

### Added

- 实现日记 CRUD 接口（`/api/diaries`）：列表 / 创建 / 详情 / 编辑 / 删除，强制用户归属校验（B1 数据层首块）

## [1.8.0] - 2026-08-05

### Added

- 鉴权路由接入日志：登录成功 / 无效 code / code2session 异常均有日志输出

## [1.7.0] - 2026-08-05

### Added

- 后台新增基于 loguru 的统一日志系统（`app/core/logging.py`）：控制台 + 文件双输出，支持级别过滤、按大小滚动、按时间保留

## [1.6.0] - 2026-08-05

### Added

- 实现微信登录鉴权接口（`POST /api/auth/login`）：接收 `wx.login` code，换取 openid，自动创建用户并签发 JWT；新增 `GET /api/auth/me` 获取当前用户

## [1.5.0] - 2026-08-05

### Added

- 完善 Pydantic Schemas 并添加验证测试

## [1.4.0] - 2026-08-05

### Added

- 启动时自动创建运行时数据目录（`ensure_dirs`）

## [1.3.0] - 2026-08-05

### Added

- 统一 `data` 目录管理运行时数据（数据库 + 上传文件），新增 `.env.example` 配置模板

### Fixed

- 数据目录管理统一为 `data/`，避免数据库与上传文件分散

## [1.2.0] - 2026-08-05

### Added

- 引入 TDD 测试框架（pytest + httpx TestClient），补充 auth 与 models 单元测试

## [1.1.0] - 2026-08-05

### Added

- FastAPI 项目初始化：包含 ORM 模型（Diary / Gear / Weight / Analysis / Checkin / Post / User）、核心配置、uv 依赖管理

## [1.0.0] - 2026-08-05

### Added

- 初始化项目基础设施（gitignore / pnpm 工作区 / VitePress 文档站点配置）

---

**docs / test / chore 类型提交**（不触发版本变更，随所属功能版本记录）：

- `docs: 修复组件桶导出导致页面空白（方案 36 + 进度表/侧边栏/AGENTS/CHANGELOG 同步）`
- `docs: Phase 2-5 我的页完成 + Phase 2 业务页面收尾`
- `docs: Phase 2-4 统计页完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2-3 装备页完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2-2 日记页完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2-1 数据层与组件库完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2 业务页面实现总纲方案文档`
- `docs: 优化 README.md 与实际进度对齐（Phase B1 后台 + Phase1 前端全部完成）`
- `docs(plans): 新增 21 前后端 .env 配置模板方案`
- `chore(miniapp): 前端配置环境变量化与 storage 键名收口`
- `chore(server): 新增 python-dotenv 与 .env.example 模板`
- `docs(plans): 新增 Phase1-8 对接 B1 登录流程方案`
- `docs(plans): 新增 Phase1-7 网络层封装方案`
- `docs(plans): 新增 Phase1-6 Pinia store 搭建方案`
- `docs(plans): 新增 Phase1-5 types 类型迁移方案`
- `docs(plans): Phase1-4 变更为 Tailwind 自定义组件方案（替代 Vant）`
- `docs(plans): 新增 Phase1-1 ~ Phase1-3 子方案文档及侧边栏配置`
- `chore(miniapp): 集成 Tailwind CSS（橄榄绿/青柠主题色，vite 内联 postcss）`
- `feat(miniapp): 目录结构与四 Tab TabBar 占位页`
- `chore(miniapp): uni-app 工程初始化`
- `docs: 新增 B1-4 基于 loguru 的日志系统方案`
- `test(server): 补充日志系统单元测试`
- `docs(plans): 新增 Phase B1 后台执行方案文档及侧边栏配置`
- `docs: 添加 VitePress 文档站点与 Tennis Diary 迁移分析方案`
- `docs: 新增 README.md 和 AGENTS.md 项目文档`
