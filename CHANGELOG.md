# Changelog

本项目的所有显著变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.86.2] - 2026-09-13

### Fixed

- CI 并行测试竞态条件（146）：`pytest-xdist` 多 worker 同时执行 `_init_test_database` 对同一 SQLite 文件 `CREATE TABLE` 导致 `table ai_providers already exists` 错误（412/741 测试失败）；修复为按 `PYTEST_XDIST_WORKER` 环境变量为每个 worker 创建独立 DB 文件，彻底消除竞态。
- CI 工作流分阶段执行：拆分为 fast 测试（并行，快速失败）+ integration 测试（`--dist loadfile` 按文件分组并行），基础测试先行，集成测试互不干扰。

## [1.86.1] - 2026-09-13

### Fixed

- Admin 事件日志查询页码未重置：点击"查询"按钮时若当前页非第 1 页（如 page=2），仍沿用旧页码发送请求，导致查到空结果；修复为查询前始终重置到 page=1。

## [1.86.0] - 2026-09-13

### Added

- AI 评分 JSON 解析容错与重试（145）：`extract_json` 增加 `json-repair` 修复层，可自动修复 LLM 返回的常见 JSON 格式问题（未转义引号、trailing comma、缺失逗号等）；`analyze_swing` 首次解析失败后自动重试 1 次（LLM 输出具有随机性）；修复仍失败时记录原始 AI 响应文本前 500 字符便于事后诊断；新增 9 个 `extract_json` 单元测试。

## [1.85.1] - 2026-09-11

### Fixed

- 电子教练界面被整文件改写、视觉结构偏离原设计（141 回归）：恢复 `coach.vue` / `report.vue` 原始 UI（hero 卡 / `Empty` 空态 / 评分圆徽 / 六维进度条 / NTRP 说明 / 删除按钮等），仅保留「缓存优先渲染」与「离线媒体占位」的数据来源改造，不再改动既有样式与布局。
- 电子教练列表误弹「本地空间不足，请先登录同步」（141 回归）：`storageBase.persist` 新增 `silent` 选项，`cloudCache` 列表/详情缓存写入改为静默（超容量/异常只丢弃不弹 toast）；该提示仅保留给游客/登录态主动新建的离线待同步数据，登录态只读浏览不再误弹。
- 分析列表缓存体积过大易超限：列表缓存仅保留渲染所需轻量字段（剥离 `report`/`pose`/`highlights`/`video_url`）并丢弃 dataURL 封面（离线统一显示占位图），详情缓存保留文字报告仅丢弃 dataURL 封面，确保离线快照稳定写入。

## [1.85.0] - 2026-09-11

### Added

- 登录态离线缓存与自动同步（141）：日记/装备/体重列表与详情渲染源统一收敛为本地缓存合并视图（`merge(账号云端快照缓存, 账号离线待同步仓库)`），页面先 hydrate 缓存立即渲染、仅网络可用且已登录才拉取远端刷新缓存；断网可浏览缓存并新建记录（落按 userId 隔离的 `td_offline_{userId}_*`），恢复后按 `business_time` 升序自动静默同步，冲突按时间戳后写胜；分析记录可离线浏览列表与文字报告、视频/封面等媒体离线统一占位不破图；含离线横幅、待同步标记、加载态（loading）三态与媒体 `resolveMediaSrc` 占位；新增 `storageBase`/`offlineRepo`/`cloudCache`/`utils/media`/`utils/network`，游客态现有本地降级机制（129）零改动。

## [1.84.0] - 2026-09-09

### Added

- 视频分片上传与断点续传（140）：大视频（≥20MB）按 5MB 切片串行上传，单片失败只重传该片，中断后仅补传缺失/失败分片。后端新增存储原语 `file_store`（`data.bin` 定位写 `os.pwrite` + `manifest.json` 权威登记 + 原子写 + 24h 过期清理）与门面 `file_service`（`open_chunk_session` / `register_chunk` / `list_chunks` / `chunk_status` / `complete_chunk_upload`，片级 `length` 强制 + `crc32` 可选校验、写盘成功才入账、complete 免合并直接 `register`），新增端点 `POST /upload/video/chunk`、`GET /upload/video/chunks`、`POST /upload/video/complete`，`/upload/check` video 未命中时下发分片策略与三集合进度，Admin `/cleanup` 联动清理过期会话。
- 小程序端分片链路（140）：新增 `utils/crc32.ts`（表驱动 CRC32）与 `utils/chunkUpload.ts`（切片读写、串行上传、单片重试、按服务端 `missing`/`failed` 断点续传、409 局部重传一次后降级整体上传），`upload.ts` 增 `ChunkPlan` 下发解析，`analyze.vue` 三分支接入（秒传 / 分片 / 整体）并展示「已传 n/m 片」进度与 `video_chunk_*` 埋点。

## [1.83.1] - 2026-09-09

### Added

- 分析事件与存储常量收口（139）：`ANALYSIS_EVENTS.started`（`utils/index.ts` 导出，配合 `uni.$emit` / `uni.$on` 跨页面通信）与 `STORAGE_KEYS.pendingAnalysisAt`（`constants/storage.ts`），避免两处硬编码导致事件名/键名漂移。

### Fixed

- 上传阶段返回列表后新记录需手动下拉才显示（139）：点「开始分析」后先进入 upload 阶段上传视频，分析记录要等 `startAnalysis()` 返回（`analysisId` 产生）才创建，此时若用户已返回列表则 `onShow` 刷新查不到、且后续不会自动补刷。现点开始时写入「启动中」标记，`start` 成功后清除并 `uni.$emit` 通知列表立即刷新；列表 `onShow` 时若标记仍在则 3 秒后补刷一次兜底（覆盖页面销毁后 JS 未继续执行、`emit` 未送达的场景）；`resetProgressState()` 统一清除标记，覆盖成功/失败/取消所有收尾路径。
- 抽帧登记触发 UNIQUE constraint 冲突导致整条分析失败（139）：`_process_video` 的 `FileDraft` 原先未传 md5/size，`register_batch` 内部 `md5s` 为空时跳过 `existing_map` 查询，随后实时计算 md5 直接 INSERT，撞上同 `user_id` 已存在的 `(user_id, md5)` 唯一索引 `uq_files_user_md5_active` 抛 `IntegrityError`。现构造 draft 时预计算 `md5`（`file_store.md5_of`）与 `size`（`os.path.getsize`），命中已存在记录时走复用分支。
- 报告页把后端 SQL 异常原文显示给终端用户（139）：失败时 `pipeline_status.error` 原文（如 `(sqlite3.IntegrityError) UNIQUE constraint failed: files.user_id, files.md5`）被直接作为摘要展示，既难懂又泄漏 schema / md5 等内部信息。现新增 FormatUserError 风格脱敏：技术性异常（`sqlite3.*` / `UNIQUE constraint` / `IntegrityError` / `sqlalchemy` / SQL 关键字 / `sqlalche.me` 链接）统一降级为「分析失败，请重新上传视频（服务端处理异常，已记录到日志）」，业务类错误（如「片段起点/终点超出视频范围」）原样透传。
- 失败态从报告体内的小 banner 提升为独立展示（139）：与 `processing-block` 互斥的独立 `failed-block`（图标 + 标题 + 原因 + 删除按钮），移除报告体内不可达的冗余 banner。
- 从列表重新进入失败记录看不到失败原因（139）：后端置 failed 时只写 `pipeline_status.error`，而 `Analysis` 响应**不含** `pipeline_status` 字段，导致重新进入时只能显示兜底文案。现三处置 failed 同步写 `summary`（截断至 120 字符：`run_pipeline` except 分支写异常原因、`_force_fail` 独立连接兜底、`_finalize` 空 `video_url` 写「播放短片缺失，分析未完成」），前端统一从 `summary` 读取并脱敏，覆盖「停留报告页失败」与「从列表重新进入」两个场景。
- 订阅超时后页面卡死（139，Step 9 引入的回归）：给 `PollingSubscriber` 加 5 分钟超时自停后，`analyze.vue` 因未传 `onTimeout` 导致 `await new Promise(...)` 永不 settle，模态永久卡在「AI 分析进行中」，比修复前更糟。现补 `onTimeout`：停止订阅 + 记录 `analysis_subscribe_timeout` 埋点 + `reject`，由既有 `catch/finally` 统一 toast 并 `resetProgressState()` 关闭模态。

## [1.83.0] - 2026-09-08

### Added

- 孤儿 processing 记录超时清理（139）：新增 `app/services/analysis_cleanup.py`，超过阈值（默认 600s）仍为 `processing` 的记录强制置 `failed` 并写入 `pipeline_status.error`「分析超时，已自动置为失败」；`created_at > 0` 条件排除历史脏数据避免误伤；接入应用启动（`force=True`）与 `list_analyses` 惰性触发（5 分钟节流）。作为状态兜底之外的最后一道防线，终结卡死记录导致的小程序端无限轮询。
- 可降级项打标（139）：新增 `PipelineEngine._mark_degraded()`，骨架文件登记等可降级项失败时写入 `pipeline_status.degraded`，保留降级完成能力但必须可观测。

### Fixed

- 管线异常中断后分析记录永久停留在 `processing`（139）：`file_service.register_batch` 的 `db.flush()` 失败未 rollback，导致调用方会话残留 pending-rollback 坏状态，后续所有 DB 操作（含 `status="failed"`）连带失败。现补 `try/rollback`。
- 管线状态兜底（139）：新增 `_force_fail()` 用**独立连接**置 `failed`；`run_pipeline` except 分支先 `rollback()` 再写 `failed`，仍失败则自动启用独立连接兜底，确保异常中断时状态必定落地。
- 管线步骤异常由「静默继续」改为 fail-fast（139）：抽帧/播放短片登记由「非致命」改为致命并直接抛出，新增 0 帧硬校验，杜绝带着空输入跑 AI/pose 产出「已完成」的垃圾报告；`_finalize` 遇 `video_url` 为空由仅 warn 保留 processing 孤儿改为置 `failed` 并写入错误原因。
- 日志 `%s` 占位符失效导致真实异常被吞（139）：loguru 使用 `str.format()` 语义，`%s` 参数会被静默丢弃、日志只剩裸占位符——这是故障中「看不到报错」的直接原因。全量整改 34 处为 `{}` 风格，10 处异常日志改用 `log.exception`。
- 小程序离开分析页后 `/analyses/{id}/status` 轮询不停（139）：页面清理由 Vue 的 `onUnmounted` 改为 uni-app 的 `onUnload`（小程序页面销毁时前者不保证触发）；`PollingSubscriber` 增加 5 分钟上限与 `onTimeout` 回调，超时停止并提示用户。
- 列表页 4s 自动轮询改为用户主动下拉刷新（139）：`pages.json` 启用 `enablePullDownRefresh`，`coach.vue` 改 `onPullDownRefresh`，消除后端卡 processing 时的无限请求。

## [1.82.0] - 2026-09-08

### Added

- 视频上传两步秒传后端端点（137）：新增 `POST /api/upload/video`（经 `file_service` 门面 `register` 落盘 `{md5}.{ext}`，视频无微信官方检测能力 → 上传阶段直接置 `security_checked=1`，返回 `{url, file_id, mirage}`）；`POST /api/upload/check` 返回 `file_id`，新增可选 `category` 做来源隔离、`size_bytes` 一致性校验；`POST /api/analyses/start` 改为 JSON 凭 `file_id` 启动（校验归属/来源/物理存在 → 建 Analysis 占位 → `bind(analysis, field="source")` → 后台管线）；门面新增 `find_by_id`，`find_by_md5` 支持可选分类。
- 小程序端两步取文件与上传/分析进度体验（137）：选视频后异步预计算 MD5 + size 指纹；`/upload/check` 命中零流量取 `file_id`，未命中再整体上传（`timeout` 按体积自适应 clamp(MB×3s, 120s, 300s)，`manifest` 补 `networkTimeout.uploadFile`）；上传/分析期间全屏模态居中显示进度并阻断误操作（进入前暂停并隐藏原生 `video`）；新增「取消上传」（含预检阶段取消检查点与 1.5s 兜底收尾），取消后保留视频与指纹可直接重试；列表 `processing` 态（⏳ 角标 + 「分析进行中…」+ 4s 轮询）与报告页实时进度页（完成后自动重载完整报告，失败展示管线错误）。

### Removed

- 移除无效视频安全检查：`video.py` 的 `check_media_sync(media_type=3)`（微信内容安全三件套不支持视频，恒返回 `errcode 40004`，是视频 `security_checked` 恒为 0 的根因）及 `content_security` 中对应的 `check_media` / `check_media_sync` 死代码。

## [1.81.0] - 2026-09-07

### Added

- 文件管理重构（138）：后端文件操作全面收口到 `file_service` 统一门面，内部分工为 `file_store`（物理存储：MD5 命名、路径推导、写盘删盘、MIME 兜底）、`file_refs`（业务引用注册表，声明哪些表哪些字段引用受管文件，支持 column / json_list / json_dict / 外键列四类提取器）、`file_ref_service`（引用计数唯一变更实现）。路由层与 `pose_service`/`video_service`/`pipeline` 禁止自造文件名、自写盘、自改 `ref_count`、直接操作 File 模型，由 `tests/test_file_architecture.py` 架构守卫测试持续约束。受管文件名统一为 `{md5}.{后缀}`，存于 `UPLOAD_DIR/{avatars|gears|videos}/{user_id}/`（目录结构不变，小程序端无需改动）。新增 `file_bindings` 绑定表作为引用计数的唯一事实来源，`bind`/`unbind`/`rebind` 幂等，业务关联时自动 +1、删除或换图时自动 -1，归零后由 `cleanup_unbound` 在宽限期回收。扫描改为基于业务引用注册表的五态分类：`in_use` / `unreferenced` / `missing` / `orphan` / `unregistered_ref`。新增 `migrate_to_md5`（支持预演、幂等）与 Alembic 迁移 `b7d41e0c9a35`、`d4e8b2f17c09`；管理端新增「存量迁移」按钮（先预演后执行）。

### Changed

- 文件记录唯一性语义调整（138）：`files` 表新增部分唯一索引 `(user_id, md5) WHERE deleted_at IS NULL`，同一用户同一内容只保留一条记录；移除与之冲突的 `uq_files_original_name` 全局同名约束。`ref_count` 默认值改为 `0`，语义由「重复记录条数」变为「业务引用次数」。秒传语义由「新建记录复用路径」改为「按 MD5 命中已有记录直接返回同一路径」。

### Fixed

- `server/.gitignore` 的 `models/` 规则未锚定到根目录，会连带忽略 `server/app/models/` 下的 ORM 模型源文件，导致新增模型文件不被 git 跟踪。改为 `/models/` 仅忽略根级 MediaPipe 模型目录。
- 文档构建（VitePress）：`docs/plans/38-*.md` 三处代码块误将「行号:行号:路径」当作语言标记，另有 `24-*.md`、`63-*.md` 使用 `env` 语言（不在 shiki 默认 bundle 中），导致 `pnpm run docs:build` 报 "language is not loaded" 并失败。修正后构建通过。

## [1.80.0] - 2026-09-06

### Added

- 文件秒传预检与安全检查标记（136）：新增 `/upload/check` 端点（MD5 + size 预检，三态响应：命中+安全通过/命中+安全未通过/未命中），`files` 表新增 `security_checked` 字段（0=未检/1=通过），上传端点改为「安全检查不通过仍落盘但标记 security_checked=0」；前端新增 `uploadFileWithCheck` 两步上传（先 MD5 预检，命中零流量返回 URL，未命中正常上传），装备封面/头像表单接入预检流程。新增 Alembic 迁移、13 条端点用例、270+ 行方案文档。

## [1.79.0] - 2026-09-05

### Added

- 游客同步顺序修复与业务时间字段（135）：新增 `business_time` 字段（Float，UTC Unix 时间戳），记录用户真实创建时间。游客同步时传入本地 `createdAt`，正常创建时为 `null`；`sync.ts` 对 pending 列表按 `createdAt` 升序排序再上传，确保服务器 `created_at` 相对顺序正确（双重保障）。三表（diaries/gears/weight_records）ORM 模型、6 个 Pydantic Schema、3 个路由文件、3 个 Admin 页面（列+弹窗）、小程序类型定义/Store/sync 全链路接入。

## [1.78.1] - 2026-09-05

### Fixed

- 小程序体重趋势图绘制顺序修复：`weightData` 用 `.sort(ascending)` 对相同日期记录无效（稳定排序保留原降序），导致图表与列表同向（最新在左）。改为 `.reverse()` 直接转升序，游客/登录模式通用。

## [1.78.0] - 2026-09-04

### Added

- 文件登记 MIME 类型兜底与分类源补全（131）：Step 116 只修了上传端点的 mime 探测，骨架视频/封面、裁剪播放短片、报告落库、孤儿文件注册等登记入口仍依赖调用方手传 `mime_type`，而这些调用方全都没传，导致大量骨架衍生文件落库为空（如 `1788331858328_8f1245f6_seg0_thumb.jpg` 文件类型显示 `--`）。修复：`file_service` 新增 `resolve_mime_type()` 由登记函数统一兜底——调用方有值则不覆盖，`get_or_create_file` / `register_orphan_files` 走 PIL/ffprobe 真实探测，`batch_get_or_create_files` 仅用确定性扩展名映射（零磁盘 I/O，保住 121 优化契约）；秒传分支改为 `existing.mime_type or <探测值>`，存量空值不再被复制扩散。新增 `ANALYSIS_MATCH_SOURCES`（含 `skeleton_video`/`skeleton_thumb`/`skeleton_frame`），修复骨架文件在无 `business_id` 时被误判「未绑定业务记录」；报告落库 `upload_source` 细化为 video/analysis_thumb/skeleton_video/skeleton_thumb/skeleton_frame；统一分析上传改用 `detect_media_mime` 与 video.py 对齐。存量空 mime 由 Admin「修复文件类型」按钮补齐。新增 25 条用例，全量无回归。

### Fixed

- 测试脆弱性治理（132/133）：全量 `pytest` 长期 10 failed，逐一排查确认均为改动前既有的脆弱测试。A 类死测试/过期断言：秒传共享删除用例插入两条同名 `original_name` 违反 `files.original_name` 唯一约束；两处用例引用 Step 125 已删除的 `register_ai_files`（改走 `batch_get_or_create_files`）；两处断言已下线的 preview 端点返回 200（另有两处断言 404 属假绿，整类删除）；裁剪用例断言「原文件已删」与 118 起保留原片语义冲突（改为断言保留）。B/C 类 fixture 作用域错配：admin `conftest` 的 module 级 `test_db`/`client` 与根 `conftest` 的 function 级 `client` 都用 `clear() + update(saved)` 操作 `app.dependency_overrides`，互相抹掉对方覆盖使请求打到错误数据库；`auth_client` 又把 admin token 写进 session 级共享 TestClient 默认头且从不清理，导致 media query token 用例 401。修复：两处 `client` fixture 改为精准增删（`set_override` 保存旧值 + teardown 还原），`auth_client` teardown 移除 `X-Auth-Token` 头，新增 autouse fixture 在每个用例前后 `test_db.rollback()` 杜绝 `PendingRollbackError` 级联，并把 roles/ai-providers 两个顺序依赖用例改为自包含。受影响子集 145 passed / 0 failed。CI 并行（ubuntu-latest, 4 workers）仍报 223 errors：root `conftest.py` 的 `test_engine` 使用 `sqlite://` + `StaticPool`，CI 并行时 SQLite 连接未正确回收导致 `create_all` 重复建表（`table ai_providers already exists`）；`test_cleanup_orphans.py` 本地 `test_engine` 与 admin conftest module-scoped `test_engine` 同名冲突 → `ScopeMismatch`。修复：`test_engine` 改用 file-based SQLite 临时文件，移除 `StaticPool`；本地 `test_engine` 重命名为 `cleanup_engine`。全量 563 passed / 0 errors。

### Changed

- 文档（132/133）：新增/更新 `docs/plans/132-测试脆弱性治理-死测试清理与fixture作用域修复.md`（含 CI 并行 StaticPool 修复），同步 AGENTS.md 进度表、docs/README.md 文档一览与执行进度、`.vitepress/config.mts` 侧边栏。

## [1.77.9] - 2026-09-04

### Fixed

- Admin 文件管理预览图片 404（130）：Admin 静态站点（`admin.example.com`）与后端 API（`api.example.com`）跨域部署且无同源反代，而 `<img>`/`<video>`/`fetch`/`<a download>` 等浏览器原生请求不走 axios，`baseURL` 不生效——相对路径被解析到前端自身域名。`views/files/index.vue` 的 `openPreview` 直出 `/api/admin/system/files/${rel_path}` 必然 404。同此根因的还有装备详情装备图（相对路径）与文件下载（`api/files.ts` `getDownloadUrl` 返回相对路径，下载走 `fetch`/`<a>` 非 axios）。修复：新增 `admin/src/utils/fileUrl.ts` 统一解析——`fileUrl`（静态文件端点）、`avatarUrl`（头像，`avatars/`→`avatar/`）、`fileDownloadUrl`（下载端点），`http(s)://` 与 `data:` 一律原样直出，其余补 `VITE_API_BASE_URL`；接入 files/gears 两处修复项，并把 analyses/users/event-logs 三处本地重复实现收敛为公共导入（头像解析顺带补 `data:` 判定）。装备图因此兼容小程序游客态写入的 base64 dataURL（`gears.photo` 后端不校验形态，可为基础库相对路径 / `data:` / 完整 URL）。`type-check` + `build` 通过。

### Changed

- 文档（130）：新增 `docs/plans/130-Admin跨域静态资源URL统一解析.md`（跨域拓扑、7 处全量扫描清单、修复方案、验证标准），同步 AGENTS.md 进度表、docs/README.md 文档一览与执行进度、config.mts 侧边栏。

## [1.77.8] - 2026-09-04

### Added

- 日记/装备/统计游客本地降级（129）：未登录用户可完整使用日记、装备、统计（数据总览 + 体重管理）三个模块——列表浏览、新增、编辑、删除、体重记录全部落地本地 `storage`，页面顶部显示「本地模式，登录后自动同步」横幅，取代原先只展示「🔒 去登录」引导空态。新增 `services/pendingRepo.ts`（本地待同步仓库，storage 持久化，含 `localId`/`pending` 标记）、`services/localStats.ts`（本地聚合，口径对齐后端 `/api/stats`）、`services/sync.ts`（登录成功后逐条 `POST` 静默同步，成功清理本地项、失败保留待下次登录重试）；`stores/diary.ts`、`stores/gear.ts`、`stores/weight.ts` 改为双路径（游客读写本地 / 登录走云端），列表与表单对 `Diary | LocalDiary`（装备、体重同理）透明，主键由 `getEntryId()` 统一取 `id` 或 `localId`。统计页「数据总览」6 卡改为本地实时聚合，体重三格/趋势/增删基于本地项。登出与 401 后本地 pending 保留，各 tab 页 `onShow` 按 `isGuest` 从本地仓库重载内存，避免云端数据串显（多账号隔离）。
- 装备封面游客「选图即检」（129）：后端新增免鉴权端点 `POST /api/upload/guest-gear-check`（`uni.login` 一次性 code → `code_to_openid` → `check_image_sync`，**检查即弃**：不落盘、不建 File 记录、不写 DB，接口故障 fail-open）；游客选图由拆分出的 `compressToDataURL()` 压缩为本地 `data:` 后即时联网受检，`safe:true` 才写入 `form.photo`，违规/损坏图当场 toast 拦截；登录后同步仍走 `/api/upload/gear-image` 正式受检上传，构成双保险。新增 5 条端点用例（免鉴权通过 / 违规拦截 / code 非法 / 检查故障放行 / 扩展名非法），并断言临时文件清理。

### Changed

- 文档（129）：新增 `docs/plans/129-日记装备统计游客本地降级与登录同步.md`（v1.1.1，含封面安全检查路线 C 决策与勘误补强），同步 AGENTS.md 进度表、docs/README.md 文档一览与执行进度、config.mts 侧边栏。

## [1.77.7] - 2026-09-02

### Added

- 小程序日记表单「花费明细」新增高频费用学习标签（128）：本地 Pinia store（`stores/costTags.ts`）持久化各费用名目使用频次（storage 键 `td_cost_tags`），首装以默认种子兜底（场地费/教练费/网球/饮料/手胶/穿线）。表单花费卡片头部下方常驻展示频次最高的 6 个快捷标签：点击无同名明细则新增一行并自动聚焦金额输入，已有同名则不重复添加、仅聚焦已有行并轻提示；保存日记成功后 `recordUsed` 累计本次使用的名目频次、首次填写的费用类型自动入池。`App.vue` onLaunch 初始化候选池。

### Changed

- 文档（128）：新增 `docs/plans/128-日记花费明细学习标签.md`，同步 AGENTS.md 进度表、docs/README.md 文档一览与执行进度、config.mts 侧边栏。

## [1.77.6] - 2026-09-02

### Fixed

- 小程序日记表单「配套装备」选择与手输被挤压（108）：从已有装备选择功能合入即存在结构缺陷——`width:100%` 的「从已有装备选择」选择器被塞进不换行的 flex 单行 `.form-gear-row` 内，把名称/体验输入框与删除键压缩到几乎不可见，导致选择装备后看不到名称填入、手输框也点不到。修复：`.form-gear-row` 加 `flex-wrap`，`.form-gear-select` 改 `flex:0 0 100%` 使其独立换行为上方一整行，输入框与删除键正常排布在下行（上下堆叠，符合 UI 设计）。新增 `gearSelectLabel(i)` 选中回显：已填名称（选择或手输）时按钮文案显示 `✓ 名称`，否则显示默认「📋 从已有装备选择」，消除"赋值后无反馈"的困惑。`type-check` + `build:mp-weixin` 通过。

### Changed

- 文档（108）：方案文档置为 🏁 已完成（v1.1.0），记录根因 git diff 与修复方案；同步 AGENTS.md 进度表、docs/README.md 文档一览与执行进度。

## [1.77.5] - 2026-09-02

### Fixed

- 小程序事件日志 `logWarn` 达到批量阈值（≥5）时整批丢失的 P0 缺陷（127）：`batchFlush()` 仅设置 3s 定时器、回调时才读取待发数组，而旧 `logWarn` 在触发阈值后随即清空数组，导致该批 warn 3s 后读到空数组全部丢失。改为抽出 `flushBatchNow()`（清定时器+取走批次+逐条上报），`logWarn` ≥5 条立即发送（真正实现「≥5 立即触发」），否则走 3s 防抖；`logInfo` 维持批量 3s。

### Changed

- 小程序 console 噪音清理（127）：删除 `App.vue` 生命周期日志、`services/request.ts` 每请求 success/fail 日志，以及各 store/页面 `logError` 后重复的 `console.error` 双写（4 store + stats/share/analyze 页），仅保留 `eventLogger` 上报失败的合理提示。
- 小程序上传/请求封装统一（127）：`pages/coach/analyze.vue` 裸 `uni.uploadFile`（手拼 baseURL + `"td_token"` 魔法字符串）改走 `utils/upload.ts` 的 `uploadRaw`，token/URL/响应解析统一；`services/analysisStatus.ts` token 键改 `STORAGE_KEYS.token`。
- 小程序死代码清理（127）：`analysisStatus.ts` 删除 SSE 全套死代码（`SSESubscriber`/`isChunkedSupported`/`arrayBufferToString`/`getAnalysisStatus`），精简为纯轮询；`services/auth.ts` 删除无引用 `getMe`；`services/data.ts` 删除无引用 `getCheckins`/`createCheckin`；`utils/index.ts` `resolveUploadUrl` 合并 `gears`/`videos` 相同分支并更正注释。
- 小程序定时器生命周期修复（127）：`pages/share/share.vue` 保存图片超时定时器提升为模块级句柄并新增 `onUnload` 清理，避免离开页面后仍弹「保存超时」toast。
- 文档同步（127）：新增 `docs/plans/127-小程序端代码卫生与健壮性优化.md`，同步 AGENTS.md 进度表、docs/README.md、config.mts 侧边栏。

## [1.77.4] - 2026-09-02

### Fixed

- 小程序昵称输入隐私授权修复为**主动引导**方案（126）：真机实测 v2.0.0「依赖微信自动弹窗」不可控——`input type="nickname"` 未授权时静默降级为 `text` 且不触发 `onNeedPrivacyAuthorization`。改为：进入页面保持普通 `text` 输入避免降级；点击昵称（用户手势内）先 `checkPrivacySetting` 查状态，需授权时 `requirePrivacyAuthorize` 拉起官方弹窗，同意后 `:key` 重建为 `type="nickname"` 并聚焦弹出微信昵称选择，拒绝则保持手动输入一次轻提示；`privacyPrompting`/`privacyAttempted` 防重入与防反复打扰。新增 `privacy.ts` 的 `checkPrivacySetting`/`requirePrivacyAuthorize`/`openPrivacyContract`（回调式 API Promise 化，低版本基础库兜底），`env.d.ts` 隐私接口类型改为回调式。

### Changed

- 小程序渲染层错误埋点分级（126）：`App.vue` `wx.onError` 白名单（`showShareMenu`/`getPrivacySetting`/`nickname`/`showNicknameAccessory`）由「整段过滤」改为按 `logWarn` 低打扰上报，其余仍按 `logFatal` 上报，避免掩盖真实逻辑层错误。
- 小程序「我的」页登录并发守卫（126）：`doLogin` 增加 `loggingIn` 标记，快速连点不重复弹 `showLoading`，保证与 `hideLoading` 配对。
- 小程序资料编辑页清理重复的 `onShow` 块（126）。

## [1.77.3] - 2026-09-02

### Added

- 小程序渲染层错误全局埋点：`App.vue` 添加 `wx.onError` 监听，上报非关键渲染层错误（126）。

## [1.77.2] - 2026-09-02

### Fixed

- 小程序昵称输入隐私授权修复：`input type="nickname"` 点击时调用 `wx.requirePrivacyAuthorize` 弹出官方隐私授权弹窗，解决 `errno:104` 降级问题（126）。

## [1.77.1] - 2026-09-02

### Changed

- Admin 文件管理端点精简：删除 `GET /files/{id}`（未使用）、`GET /files/{id}/preview`（前端直接构造 URL）、`POST /files/register-all`（合并到 `/register` 空列表触发），端点数 13→11（125）。
- Admin 文件管理 Schema 精简：移除 `DerivedFileInfo` 类和 `AdminFileResponse.derived_files` 字段（列表不展示，详情端点已删），Schema 类 7→5（125）。
- Admin 文件注册接口统一：`POST /register` 支持空 `files` 列表自动扫描并注册全部孤儿，替代原 `register-all` 端点（125）。

### Fixed

- Admin 文件列表 N+1 查询修复：移除 `_file_to_response` 中每条文件单独查询派生文件的逻辑（表格不展示），每页省 20 次查询（125）。
- Admin 文件列表分类查询统一：非 `usage_status` 筛选路径也使用 `bulk_classify_files` 批量分类，替代逐条 `classify_file_usage`（每次查 3 张表），classify 查询从 O(N×K) 降到 O(N)（125）。
- Admin 文件统计 `unreferenced_count` 查询优化：用 `bulk_classify_files` 替代全表逐条分类循环（125）。

## [1.77.0] - 2026-09-01

### Added

- Admin 分析报告筛选功能：后端新增 `date_from`/`date_to`/`kind`/`mode`/`status` 五个筛选参数，前端新增筛选区域 UI（日期范围、类型、模式、状态下拉）+ 查询/重置按钮（124）。
- Admin 分析报告行点击查看详情：表格行直接点击打开详情弹窗，无需点击"查看"按钮（124）。
- Admin Table 组件样式增强：单元格交界添加短竖线分隔（16px 居中），操作列使用 flex 居中显示。

### Changed

- Admin 分析报告列宽优化：隐藏冗余的 `date` 列，为各列添加 `width` 属性（124）。
- Admin Table 组件单元格 padding 调整：`py-4`（16px）→ `py-2.5`（10px），行高更紧凑。
- Admin 分析报告封面图片尺寸缩小：`h-10 w-16`（40x64px）→ `h-8 w-12`（32x48px）。

### Fixed

- Admin 分析报告创建时间显示 1970/1/22：前端错误使用 `formatDate`（期望 ISO 字符串），改为 `formatTs`（Unix 秒级时间戳）（124）。
- Admin 分析报告排序混乱：只按 `date` 排序导致同一天内记录顺序不稳定，新增 `id` 作为二级排序（124）。

## [1.76.13] - 2026-09-01

### Fixed

- 综合分析骨骼视频帧数修复：`pipeline._compute_pose` 在 full 模式下传入 `full_frames=True`，骨架视频帧数与原视频一致（123）。
- 骨架缩略图独立化：`pose_service` 编码骨架视频后自动提取首帧作为 `_thumb.jpg`，不再依赖 `sk_0000.jpg`（123）。
- 骨架帧不落库不登记：`pipeline._write_pose_result` 和 `pose._persist_pose` 不再将骨架帧写入 DB 或注册为 File 记录，分析完成后自动清理（123）。
- 中间帧统一清理：`pipeline._cleanup_intermediate_frames` 同时清理 `_f*.jpg`（抽样帧）和 `_sk*.jpg`（骨架帧）（123）。
- 删除分析兜底清理：`file_service.decrement_analysis_files` 调用 `_cleanup_orphan_intermediate_frames` 兜底清理残留文件（123）。
- Admin 分析弹窗骨架帧替换为视频播放器，解决图片列表过长问题（123）。

## [1.76.12] - 2026-08-31

### Added

- 裁剪视频纳入文件管理：管线 `_process_video` 中将裁剪视频（`_seg0.mp4`）登记到 File 表（`upload_source=video_playback`），Admin 文件管理界面可见。
- 管线完成后自动清理采样帧：`_finalize` 中删除 `_f{i}.jpg` 文件（AI/姿态推理的中间数据），释放磁盘空间。

### Changed

- `pose.skeleton_thumb` 冗余字段移除：pose JSON 不再包含 `skeleton_thumb`，改用 `analysis.thumb`；Admin 分析详情页适配为读取 `a.thumb`。

## [1.76.11] - 2026-08-31

### Added

- `compute_md5_and_size()`：一次磁盘读取同时计算 MD5 和文件大小，避免重复 I/O。
- `batch_get_or_create_files()`：批量文件登记函数，一次查询 MD5 去重 + 一次 bulk insert，替代逐帧串行调用。
- `tests/test_file_service_batch.py`：10 个测试用例覆盖批量函数的正常/异常/混合场景。

### Changed

- `pose_service` 骨架帧预计算：`_analyze_full_frames` 和 `_analyze_sampled_frames` 在写入磁盘时同步计算 MD5/size，返回结构改为 `[{rel_path, md5, size, upload_source}, ...]`。
- `pipeline._write_pose_result` 改为批量模式：骨架帧/视频/封面合并为一次 `batch_get_or_create_files` 调用，两次 `db.commit()` 合并为一次。
- 状态查询端点返回 `skeleton_video_info` / `skeleton_thumb_info` 替代原有 `skeleton_video_url` / `skeleton_thumb`。

### Fixed

- Pipeline 写表步骤 N+1 查询问题：骨架帧逐帧串行 `get_or_create_file` 改为批量插入，DB 操作从 ~427 次降至 ~3 次，写表耗时从 56.5s 降至 <1s。
- `ensure_unique_name` 批量优化：批量预查询 original_name 集合，内存内计算唯一名称，避免逐条 DB 查询。
- pose JSON 写入格式兼容旧版：`_write_pose_result` 写入 DB 前将 `skeleton_frames` 从字典数组转为字符串数组，保持前端期望的旧格式；同时迁移修复已有 Analysis 记录。

## [1.76.10] - 2026-08-30

### Added

- Pipeline 各步骤耗时日志：`run_pipeline` / `_process_video` / `_compute_ai` / `_compute_pose` / `_finalize` 各阶段增加 `time.time()` 计时，日志输出 `管线-视频处理耗时` / `管线-AI评分耗时` / `管线-姿态推理耗时` / `管线-并行计算耗时` / `管线-写表耗时` / `管线完成 total=`。
- `pipeline_status` JSON 增加顶层计时字段：`started_at` / `completed_at` / `total_duration_s` / `parallel_duration_s`，每个步骤 dict 增加 `duration_s`。

### Changed

- 前端移除旧 118 串行调用：删除 `analyze.vue` 中 `startAnalysis()` 函数（~190行）、`useUnifiedMode` flag、旧 imports；`handleStartAnalysis()` 直接调用 `startAnalysisUnified()`。
- 前端 `data.ts` 移除旧端点函数：`uploadVideo()` / `analyzeSwing()` / `analyzePose()` / `createAnalysisInit()` / `finalizeAnalysis()`，保留 `generateCaption()` / `createAnalysis()` / `getAnalyses()` 等。

### Fixed

- 管线并发 Session 冲突修复：`PipelineEngine` 拆分为「计算并行 + 写表串行」架构，AI 与姿态检测在 ThreadPoolExecutor 并行执行，DB 写入（score/summary/pose/骨架文件登记）在主线程串行完成，消除 SQLite `InterfaceError: concurrent operations are not permitted`。
- 管线后台任务 async→def：`run_in_threadpool` 包裹的后台任务函数改为同步 def，避免 Starlette 线程池不执行协程导致事件循环阻塞。
- 事件端点 async→def：`/api/events` 端点改为同步 def，修复阻塞事件循环导致小程序埋点上报超时。
- `_compute_ai` 不再使用 DB：AI 配置由主线程预读传入，线程内仅执行纯计算，避免跨线程 Session 冲突。
- `probe_frame_rate` 帧率探测修复：`-show_entries stream=r_frame_rate,avg_frame_rate` 多行输出导致 `split("/")` 解析失败，回退默认30fps；改为只请求 `r_frame_rate` 并加 `split("\n")[0]` 防御。
- 骨架视频帧率上限移除：`min(30.0, fps)` 硬上限导致60fps视频骨架播放速度减半，移除后保持原帧率。
- 批量文件登记 savepoint 隔离：`get_or_create_file` 内 `db.flush()` 约束失败后 session 进入 prepared 状态，后续操作全部报错；改为 `db.begin_nested()` savepoint，单条失败仅回滚该条。
- `get_or_create_file` 批量插入去重：加 `db.flush()` 确保后续 `ensure_unique_name` 能看到前一条记录，避免同名冲突。
- `get_or_create_file` MD5/size 内部计算：调用方只需传 `abs_path`，消除各处重复的 `compute_md5_from_path` / `compute_md5_from_bytes` + `get_file_size` 调用。
- 文件登记统一为 `get_or_create_file`：删除 `register_ai_files` 函数，所有文件登记走同一入口，按 `upload_source` 区分类型。
- 管线并行步骤异常收集：AI+pose 两个 future 的异常均被捕获，合并错误信息，不再静默丢失。
- 管线失败状态提示：历史列表显示红色 ✕ 徽章 + "分析失败"，报告页顶部红色横幅。
- 文件登记统一为 `get_or_create_file`：`analyses.py`、`pose.py`、`video.py`、`upload.py` 所有文件登记调用统一，删除 `register_ai_files` 函数。

## [1.76.9] - 2026-08-30

### Fixed

- 文件名全局唯一：`ensure_unique_name` 去掉 `user_id` 过滤，全用户范围检查重名；DB 唯一约束从 `(user_id, original_name)` 改为 `(original_name)`；`register_ai_files` 每次 `db.add` 后 `flush` 确保同批次去重可见。

## [1.76.8] - 2026-08-30

### Fixed

- `ensure_unique_name` 去重检查包含软删除记录：原逻辑仅查 `deleted_at IS NULL`，但 UNIQUE 约束 `(user_id, original_name)` 包含所有行，软删除记录仍占位导致 INSERT 报 `UNIQUE constraint failed`。

## [1.76.7] - 2026-08-30

### Fixed

- 秒传路径修复：`video.py` 秒传分支错误使用新生成的 UUID 路径（`rel_video`），应使用已有文件的 `file_record.rel_path`，导致 ffprobe 仍指向不存在的文件。

## [1.76.6] - 2026-08-30

### Fixed

- 秒传路径物理文件存在性校验：`get_or_create_file` 增加磁盘文件检查，DB 记录存在但文件已清理时自动降级为普通上传（生成新 UUID 路径），避免 ffprobe 报 `No such file or directory`。回退 always-write 方案，恢复秒传复用已有文件路径的设计。

## [1.76.5] - 2026-08-30

### Fixed

- 视频上传秒传路径修复：秒传（mirage）仅复用 DB 记录，原始文件可能已被清理导致 ffprobe 报 `No such file or directory`。移除 `is_mirage` 条件，始终将上传内容写入磁盘。

## [1.76.4] - 2026-08-30

### Fixed

- 统一日志格式为 f-string：loguru 不支持 `%s` printf 风格参数（被忽略显示为字面量），项目内 17 处日志统一改为 f-string。
- 修正 AGENTS.md 过时的日志格式规则：明确禁止对异常对象直接 `f"...{exc}"` 拼接（`str()` 含 `{}` 触发 loguru 二次格式化崩溃），允许 `f"...{type(exc).__name__}"` 安全写法。

## [1.76.3] - 2026-08-30

### Fixed

- 视频上传排查日志：写入后记录文件存在性/size/inode，`detect_media_mime` ffprobe 失败时记录 stderr，异常处理器输出完整 `str(exc)` 消息。移除无效的 probe_duration 重试逻辑。

## [1.76.2] - 2026-08-30

### Fixed

- 视频上传 MIME 检测顺序修复：`detect_media_mime` 移到文件写入+size 校验之后，避免对尚未落盘的文件调用 ffprobe。
- `probe_duration` 文件存在性重试：写入后最多重试 3 次（每次 100ms），防止 Windows 文件系统延迟导致 ffprobe 找不到文件。
- 修复 `video_service.py` 7 处 f-string 日志违规（AGENTS.md 禁止 loguru 用 f-string）。

## [1.76.1] - 2026-08-30

### Fixed

- 文件注册表去重遗漏：`register_ai_files`（骨架帧注册）和 `register_orphan_files`（孤立文件注册）创建 File 记录时未调用 `ensure_unique_name()`，导致同名文件触发 UNIQUE constraint failed。补齐去重逻辑，冲突时自动追加 `_1`、`_2` 后缀。

## [1.76.0] - 2026-08-29

### Added

- 电子教练分析流水线重构（118）：点击即建 analysis_id，上传/AI评分/姿态三步携带 analysis_id 分步更新同一分析记录；新增 `analysis_video_info` 表登记原视频/裁剪/播放短片/骨架衍生文件；播放短片纳入文件管理，分类边界对齐（原片/抽帧为 unreferenced）；小程序 `startAnalysis` 改为 init→upload→(AI+姿态)→finalize 五步流水线。

## [1.75.6] - 2026-08-28

### Added

- 文件类型探测与 MIME 修复（116）：新增 `app/services/file_type_detector.py` 探测模块（ffprobe + magic bytes 双重检测，17 种媒体类型映射）；Admin 文件管理新增 MIME 分类筛选；批量修复脚本扫描并修正历史文件 `mime_type` 字段。

## [1.75.5] - 2026-08-27

### Fixed

- 文件/备份下载强制 octet-stream 附件并支持 token 双通道鉴权：`admin/system/files` 和 `backups` 下载端点统一返回 `application/octet-stream` + `Content-Disposition: attachment`，阻止浏览器预览行为；支持 `?token=` 查询参数与 `X-Auth-Token` 请求头双通道鉴权，解决 `<a>` 标签原生下载无法携带自定义头的问题。
- `start-server.py` 跨平台化并启用 uvicorn 热重载：改用 `sys.executable` 确保虚拟环境 Python 路径正确，`--reload` 参数移至默认启用。
- 修复 `test_cleanup_orphans` 依赖覆盖泄漏：测试 fixture 中 `monkeypatch` 的环境变量在测试结束后未恢复，影响后续用例。

## [1.75.4] - 2026-08-27

### Added

- 提交门禁改跑 fast 轻量子集：`pre-commit` hook 改为仅执行 `pytest -m fast`（纯函数/模型/校验，不依赖 DB 与 TestClient），全量集成测试移交 CI 并行执行；引入 `pytest-testmon` 实现增量测试（只跑受影响用例）。
- 测试并行化提速：引入 `pytest-xdist`（`-n auto` 并行）+ `StaticPool` 内存库 + session 级 `client` fixture，本地全量测试从 ~2min 降至 ~1min；`verify.sh` 同步改用 `-n auto`。

## [1.75.3] - 2026-08-26

### Added

- Admin 备份下载进度条：备份管理页下载复用 `downloadAdminFile` 的 `onProgress` 回调驱动 `DownloadProgress` 进度条（文件名/已下载/总大小/百分比/取消），与文件管理页下载体验一致。

## [1.75.2] - 2026-08-26

### Added

- Admin 文件流式下载（114）：Chromium 浏览器使用 `showSaveFilePicker` + `WritableStream` 实现零内存流式写入磁盘 + `DownloadProgress` 进度条（文件名/已下载/总大小/百分比/取消按钮），非 Chromium 浏览器自动 fallback 到 `<a>` 标签原生下载。

## [1.75.1] - 2026-08-26

### Fixed

- Admin 文件下载 MP4 另存为卡死修复（114）：Chrome 对 `video/mp4` 自动发送 Range 请求尝试预览，与另存为对话框并发导致 UI 线程死锁。修复方案：删除 Range 分片逻辑，改用 `StreamingResponse` 强制 `Content-Type: application/octet-stream` + `Content-Disposition: attachment`，阻止 Chrome 视频预览行为。前端下载改用 `<a>` 标签替代 `window.open`。12 个后端测试通过。

## [1.75.0] - 2026-08-26

### Added

- Admin 文件预览与分片下载（114）：新增 `GET /{file_id}/download` 端点，支持 Range 请求头实现分片下载（206 Partial Content），前端 1MB 分片 + 右下角进度条（文件名/百分比/已下载/总大小/取消按钮）；新增 `GET /{file_id}/preview` 端点返回 mime_type + preview_url，前端预览弹窗按类型渲染 img/video/audio，不支持的格式提示。表格行操作和详情弹窗底部均增加「预览」「下载」按钮。10 个后端测试通过。

## [1.74.2] - 2026-08-26

### Fixed

- 文件统计「可清除」计数修复：仅统计 `unreferenced` 状态文件，排除已软删的 `marked_deleted`（删除不可逆文件后计数保持不变）。
- 文件列表「可清除」状态筛选：前端将 `filterUsageStatus` 传给后端 `usage_status` 参数，由后端实时分类后筛选+分页，修复之前 client-side 过滤当前页数据导致筛选结果为空的问题。
- 文件详情弹窗文件名换行：原始文件名添加 `break-all`，长文件名按字符换行不再撑开弹窗。

### Performance

- usage_status 筛选批量分类：新增 `bulk_classify_files` 预加载全部用户/装备/分析记录，一次分类所有文件，避免 N+1 逐条查询（109 个文件从 ~110 次查询降至 ~5 次）。

## [1.74.1] - 2026-08-25

### Fixed

- Admin 表格宽度优化：移除 `min-w-full` 防止表格挤压侧边栏；新增 `table-layout: fixed` 真正固定列宽（`width` 从最小宽度升级为固定宽度）；支持 `wrap` 列属性，长文本无空格文件名改用 `word-break: break-all` 强制换行；其他列固定宽度、文件名列自适应填满剩余空间。公共 Table 组件增强（`columns` 新增 `wrap`/`align`/`headerClass`/`className` 属性），8 个使用页零影响。

## [1.74.0] - 2026-08-25

### Added

- 多选删除可清除文件（113）：Admin 文件管理列表支持多选并批量删除「可清除」文件（usage_status≠in_use）。公共 Table 组件增强（`columns` 支持 width/align/className，内置 `selectable` 多选列、`rowSelectable` 谓词、`selection-change` 事件、`clearSelection` 暴露方法，8 个使用页零影响）；后端抽出 `file_service.soft_delete_file` 复用单条删除逻辑，新增 `POST /api/admin/files/batch-delete` 返回 `{deleted, skipped, disk_removed, errors}`（空列表返回 400）；前端「批量删除 (N)」按钮仅对可清除文件可选。4 个后端测试通过。

## [1.73.0] - 2026-08-25

### Added

- 立即清理孤儿文件（112）：Admin 扫描弹窗新增「立即清理」按钮，物理删除选中的孤儿文件（未在 File 表中注册的文件）。`file_service.cleanup_orphan_paths(rel_paths)` 物理删除并返回成功数；`POST /api/admin/files/cleanup-orphans` 接受 `CleanupOrphansRequest{files}`，带审计日志。

### Fixed

- 修复文件统计「可清除」计数恒为 0：原用 `ref_count<=0` 聚合，但秒传机制使所有文件 `ref_count>=1`，改为逐条调用 `classify_file_usage` 计数，与列表端点逻辑一致（本地实测 in_use=65 / unreferenced=121）。

## [1.72.0] - 2026-08-25

### Added

- 文件使用标记（111）：基于数据库引用核查标记文件「使用中 / 可清除」。新增 `file_service.classify_file_usage(db, file_record) -> (usage_status, usage_reason)`，按优先级判定：已软删→marked_deleted；ref_count<=0→unreferenced；business_type+business_id 精确路径匹配→in_use/unreferenced；否则按 upload_source 主动查业务表（avatar→User、gear_image→Gear、video/video_frame/skeleton→Analysis）推断；均无引用→unreferenced。`AdminFileResponse`/`OrphanFileInfo` 新增 `usage_status`/`usage_reason`；Admin 列表/统计/扫描弹窗展示状态徽标 + 按状态客户端过滤。24 个后端测试通过。

### Fixed

- 修正 `classify_file_usage` 逻辑：移除 `business_id=None` 硬截断，改为按 `upload_source` 主动查业务表推断，使未绑定 business_id 的新上传文件（头像/装备图/视频）也能正确分类为「使用中」而非一律「可清除」。

## [1.71.0] - 2026-08-24

### Added

- 文件扫描功能（110）：Admin 文件管理新增扫描 uploads 目录功能，可发现未在 File 表中注册的孤立文件；支持批量/单个/一键"纳入管理"操作，自动推断 user_id 和 upload_source；前端新增扫描按钮与扫描结果弹窗。7 个新测试通过。

## [1.70.0] - 2026-08-24

### Added

- 文件管理系统（109）：后端新增独立 File 模型 + MD5 秒传 + ref_count 引用计数 + 软删除联动，统一路径工具到 file_service.py；新增 Admin 文件管理 API（list/detail/stats/delete/cleanup）+ Admin 文件管理前端页；小程序统一上传工具 uploadRaw/uploadFile + 事件钩子，重构 uploadAvatar/uploadGearImage/uploadVideo 三个函数；约束修复（移除 md5 UNIQUE → 新增 original_name UNIQUE，秒传恢复为新建独立记录 + 复用物理路径 + 原记录 ref_count 递增）。430 测试通过。

## [1.69.4] - 2026-08-23

### Fixed

- 小程序：埋点上报优化（107）：新增 `type` 参数支持网络/业务事件分类；`request.ts` 网络错误标记为 `network` 类型；电子教练分析流程拆分为 4 个端点级事件（video_upload/ai_swing/ai_pose/analysis_create）共享同一 traceId；头像更新/分享数据加载增加链路追踪；修复 11 处缺失 trace_id 的日志调用；补全 profile_update/diary_create 业务参数；移除无意义的页面浏览事件。
- 管理端：事件日志详情弹窗增加 trace_id 一键复制按钮（剪贴板 API + textarea 降级 + toast 提示）。

## [1.66.11] - 2026-08-22

### Fixed

- 小程序：移除电子教练选择视频的 15 秒超时限制，避免大视频在系统相册压缩时误报"选择视频超时"。

## [1.69.3] - 2026-08-22

### Fixed

- 后端：装备图片上传改用服务端文件存储（base64→URL），新增 `/api/upload/gear-image` 端点（含 `imgSecCheck`）；`media.py` `_owned()` 支持 `gears/` 路径；`decorators/audit.py` 修复 `current_user` 提取（审计日志不再 `user_id=None`）。
- 前端：装备表单/列表图片改用 `resolveUploadUrl()` 显示；`choosePhoto()` 错误传播修复 + `onPickPhoto` 错误提示。

## [1.69.2] - 2026-08-22

### Fixed

- 小程序：iOS 端电子教练选择视频转圈兼容性修复（103）：`uni.chooseVideo` → `uni.chooseMedia` 迁移（已废弃 API 替换），`mediaType: ['video']` 避免 iOS mix 模式 bug，新增 15 秒选择超时检测防止无限转圈，增强隐私声明未配置错误提示。

## [1.69.1] - 2026-08-22

### Fixed

- 后端：修复 `AdminResponse` 缺失 `role_id` 导致管理员登录 `/api/admin/auth/login` 返回 500（`ValidationError`）；同时修复全局异常处理器 `logger.error(f"...{exc}")` 的 f-string 拼接触发 loguru 二次 `.format()` 崩溃、掩盖真实错误，改为 `%s` 风格；并增强 `test_admin_login_success`/`test_get_admin_info` 对 `role_id` 与 `role` 的断言。
- 管理端：分析详情文件 URL 增加 `VITE_API_BASE_URL` 前缀，兼容非同源部署。
- 测试：`test_forehand_debug_pipeline` 在参考视频素材缺失（不入库）时整体跳过，避免干净环境误报失败。

## [1.69.0] - 2026-08-21

### Added

- 操作审计日志（102）：中间件+装饰器架构，独立审计库 audit.db，41 个写操作端点全量装饰器，Admin 前端审计日志页（列表+详情+筛选），13 个后端测试通过。

## [1.68.5] - 2026-08-21

### Fixed

- 修复时间轴开放起点标记被播放头遮挡问题（`z-index: 8` → `11`），并加粗标记宽度（2px → 4px）添加阴影增强视觉层次。
- 后端日志细化与异常静默处理修复（101）：全面审计 11 个文件 25+ 处异常处理，`pass` → log、`from None` → `from exc` + log、`exc_info=True`、`print()` → loguru，杜绝静默吞异常。

## [1.68.4] - 2026-08-21

### Fixed

- 修复时间轴开放起点标记不显示问题：补充父元素 `position: relative` 及子元素定位，添加 `z-index: 8` 确保标记不被遮挡。

## [1.68.3] - 2026-08-21

### Fixed

- 优化时间轴开放起点标记视觉样式：三角形箭头 + 竖线组合，增强"包裹感"和起点标识清晰度。

## [1.68.2] - 2026-08-21

### Changed

- 电子教练时间轴支持多段剪辑（99 时间轴）：按钮改为「设置起点/设置终点」状态切换模式，点击「设置起点」后在轨道上显示开放标记（橄榄绿竖线 + ▶），再点击「设置终点」闭合当前段；full 模式最多 8 段，single 模式仅 1 段且已有片段时禁止新开段；移除原单段修改逻辑（`setTrimToPlayhead`），统一为开闭段流程。

## [1.68.1] - 2026-08-21

### Changed

- 电子教练时间轴缩放控件改用**放大镜图标**（`.tl-glass` + 橄榄绿圆框手柄）并放置于时间轴上方两侧（左缩右放）；徽标右上角小圆叠加 `−`/`＋` 标识，半透明白底 + 阴影提升层级感。

## [1.68.0] - 2026-08-21

### Changed

- 电子教练时间轴（99）交互调整：**移除**左右起止把手（不再支持拖把手调范围），起止帧统一通过「设置起点 / 设置终点」按钮在播放头帧设定；**新增**时间轴上方透明背景放大（＋）/缩小（−）控件（×1.5 步进，clamp 至全览与 0.5s 帧级），单指拖动轨道选帧与双指捏合缩放保留。

## [1.67.2] - 2026-08-21

### Changed

- 电子教练时间轴缩放范围增强（99 时间轴）：放大极限由 2s 降至 **0.5s**（接近逐帧，便于精确对齐起止帧）；初始视野改为容器宽度自适应约显示 **4 秒**（`measureBar` 后按 `barWidth/min(duration,4)` 初始化 pps），取代固定 80px/s 导致的「短视频初始即接近全览、缩小无感」问题——现在缩短与放大均可覆盖近一个数量级（0.5s ↔ 全览）。

## [1.67.1] - 2026-08-21

### Fixed

- 修复电子教练时间轴设置起始点后无法双指缩放（99 时间轴）：把手上绑定 `catchtouchstart` 会拦截并阻止事件冒泡到容器，而起始把手恰定位在中间播放头附近，双指之一落在把手上时容器收不到触摸、无法进入 pinch。现移除把手独占事件，改为容器统一事件 + 触点命中检测（起点/终点各 24px 命中半径）。
- 时间轴刻度自适应缩放与优化：刻度步进随 pps 自动调整（相邻刻度 ≥40px，放大后细分至 0.1~0.5s），仅渲染可见时间窗刻度避免堆积；字号 9px → 11px、加粗并附刻度短线。

## [1.67.0] - 2026-08-21

### Changed

- 电子教练时间轴重构为剪映式交互（99 时间轴）：播放头固定容器中间（竖线 + 顶部菱形标记，随主题色）；完整长度视频轨道可左右拖动选帧（手指拖动 → `playhead -= dx/pps` 节流实时 seek 预览）；双指捏合缩放 pps（80px/s 基准，全览 ↔ 2s 满屏，以播放头为锚点）；轨道起止两侧新增可拖把手，拖到中间播放头 6px 内自动吸附，位置即起始/结束帧；「设置起点 / 设置终点」按钮将播放头当前帧设为裁剪边界；时间刻度以播放头为参考居中实时移动；保留多段色块点击定位、删除与重置。

## [1.66.10] - 2026-08-20

### Fixed

- 视频上传处理失败时保留 `_debug_` 副本并记录文件大小/保留路径（仅 `ValueError` 类，用于排查设备上传「无法解析视频时长」字节损坏问题，定位后清理）。
- `probe_duration` 解析失败日志改为内联 `rc=` 与 `stderr=`（此前为 loguru keyword 参数，部分日志处理链路丢失上下文）。

## [1.66.9] - 2026-08-21

### Changed

- 时间轴交互优化（99 时间轴）：播放头固定在时间轴中间（50% 位置），拖动时间轴时视野移动而播放头不动；移除纵向分区逻辑（上拖/下拖），整个时间轴区域统一为拖动操作；双指缩放以视野中心为锚点；简化 `keepInView` 逻辑；提示文案更新为「拖动时间轴选择帧 · 双指缩放」。

## [1.66.8] - 2026-08-20

### Fixed

- 修复视频上传失败时二次 `os.unlink` 抛 `FileNotFoundError` 导致 500：路由各异常分支改用 `_safe_unlink`（文件已不存在时忽略），并新增 `ValueError` 类异常（如「无法解析视频时长」）真实消息透出，便于用户/日志定位（此前一律掩盖为「视频处理失败，请检查文件格式」）。
- `probe_duration` 解析失败时记录 ffprobe/ffmpeg 返回码与 stderr 尾部（便于排查用户视频无法解析时长）。

## [1.66.7] - 2026-08-20

### Fixed

- 修复统一异常处理错误码误报：未匹配的 4xx（含 400 业务/参数错误）此前默认映射为 `10001`（未登录）——视频上传超限/裁剪非法等会返回 `{"code":10001,...}`。现新增 400 → `ErrorCode.INVALID_REQUEST`（30000），401 → `10001` 显式化，其余 403/404/422/5xx 不变；附回归测试。

## [1.66.6] - 2026-08-20

### Changed

- 解除电子教练时间轴模式时长限制（99）：`single` 15s / `full` 90s 的片段总长上限与整片统一为 **180s**（即仅保留整片上传上限兜底），支持直接把 120s+ 对拉视频在 single/full 模式直接分析或整段裁剪；服务端 `_MAX_DURATION` 与客户端 `MODE_LIMIT` 同步为 180，删除 `process_video` 中冗余的模式时长校验与「请在时间轴选择片段」提示，`validate_cuts` 总长上限随之放宽。

### Fixed

- 修复整片超限未裁剪直传（99 时间轴）：客户端 `startAnalysis` 预检查漏判「视频时长未加载（`videoDuration=0`）」场景——此时 `0 > modeLimit` 恒为假，长视频会被放行上传撞上后端费解的超限报错。现时长未加载、或整片超过 180s 上传上限时均在本地拦截。

## [1.66.5] - 2026-08-20

### Fixed

- 修复时间轴裁剪引导缺失导致整片超限直传（99 时间轴）：客户端 `startAnalysis` 预检查漏判「视频时长未加载（`videoDuration=0`）」场景——此时 `0 > modeLimit` 恒为假，整片 120s+ 视频会被放行上传，撞上后端「单次挥拍视频最长 15 秒，当前 120.2 秒」这类费解报错。现时长未加载或整片超限且未裁剪时均在本地拦截并引导到时间轴。

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
