> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 147 |
> | 文档版本 | v1.10.0 |
> | 文档状态 | 🚧 代码完成（Step 0-11），待真机/线上验收（P0 已备案外链域名 + 七牛凭据） |
> | 最后更新 | 2026-10-26 |
> | 对应功能/内容 | 阶段一细化方案：七牛 Kodo 对象存储接入（上传后同步写 S3 + 响应层下发外链 + 状态机/补偿/双删 + **文件管理 S3 同步中心** + 管理端扩展） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-10-26 | v1.5.0 | **Step 6 完成**：路径 B/C 写接线 —— `register_batch` 逐条同步、分片 `manifest["backend"]` 快照、`complete` 先 pre-put 再落库（`ChunkSyncError`→503 保持可续传）；§七 表按实现校准 |
> | 2026-10-26 | v1.6.0 | **Step 7 完成**：响应层两态外链收口 —— `ApiResponse.model_post_init` → `storage.urls.rewrite_response_urls`（字段名注册表 + 收集→单次 `IN` 查询→改写两趟遍历，幂等）；请求级会话用 `ContextVar` 绑定（async 应用级依赖，规避同步依赖线程池 Context 拷贝坑）；§6.2 按实现校准 |
> | 2026-10-26 | v1.7.0 | **Step 8 完成**：管理端 —— `scan` 新增 `pending_sync`、`missing` 重定义为「DB 有而对象存储无」（一次 `iter_keys` 全量列举核对）；§5.4 双删落地（`/cleanup`、`/cleanup-orphans` 同步删对象，失败不阻塞）；同步端点三件套 `sync-status`/`sync`/`sync/{id}` + `storage_sync_service`（scope/dry_run/force + `RUN_STATE` 防并发 409 + `BackgroundTasks` 跑批） |
> | 2026-10-26 | v1.8.0 | **Step 9 完成**：Admin 同步中心前端 —— 列表响应补 `storage`/`storage_status` 两列（单一构造点 `_file_to_response`）+ `storage_status` 查询下推筛选；文件页新增 S3 同步弹层（统计卡片/进度条/范围单选/dry_run 预览/执行 + 1.5s 轮询至任务结束）、位置与同步状态列、行内同步按钮、详情两字段；`useActionLock` 防重 + `onUnmounted` 清定时器 |
> | 2026-10-26 | v1.9.0 | **Step 10 完成**：补偿任务三触发点 + 迁移 CLI —— `find_stale`/`compensate`（grace 60s、单批 50、`backend=local` 静默 no-op、与同步中心抢跑时 conflict 跳过）、`run_startup_compensation`/`schedule_startup_compensation`（lifespan 一次性线程池任务）、`compensate_after_upload`（同用户小批量、异常不外抛）接入 avatar/gear-image/video 三上传端点、`scripts/migrate-files-to-kodo.py`（与同步中心共用 `plan`/`run_sync`）；另修 409 用例顺序依赖（xdist 下暴露） |
> | 2026-10-26 | v1.10.0 | **Step 11 回归完成**：全量 `pytest -n auto` **874 passed / 0 failed**（修复预存 `test_forehand_video_processed` 过期断言）、`ruff` 干净、fast 355、admin + miniapp type-check/build、`docs:build` 全绿；§十一 验收清单逐项标注状态（11 项自动化 🤖 / 3 项待线上 ⏳）；文档状态细化为「代码完成，待真机/线上验收」 |
> | 2026-10-26 | v1.4.0 | **Step 1-5 完成**：`StorageBackend` 抽象 + local/kodo/memory 三实现 + 工厂快照缓存（Step 1/2）、`storage` 分类 9 项配置（Step 3）、`files` 两列迁移 `c7a147f0b3d5`（Step 4）、路径 A `register` 写接线 + `sync_to_storage` 状态流转（Step 5）；fast 门禁 285 passed |
> | 2026-10-26 | v1.3.0 | **Step 0.5 完成**：Windows `os.pwrite` 兼容修复（§十四 标记已修、§十五 新增 Step 0.5 行）；`pytest -m fast` 225 passed 全绿 |
> | 2026-10-26 | v1.2.0 | **Step 0 完成**：§6.3 资源接入清单按 `file_refs.FILE_REF_SPECS` 盘点定稿（5 类接入点 + 4 项「不接入」+ 3 条关键发现）；§十四 记录基线风险（Windows `os.pwrite` 致 18 用例失败）；文档状态 📋 → 🚧 |
> | 2026-10-26 | v1.1.0 | **新增 §9.1 文件管理 S3 同步功能**（同步中心端点 + `storage_sync_service` 共用服务 + Admin 文件页弹层/状态列/筛选）；TDD 步骤插入 Step 9、验收 +3 例、工作量 6~9 → 7~10 人日 |
> | 2026-10-26 | v1.0.0 | 初版（范围/架构/数据模型/配置/流程状态机/读路径外链/三类文件改造/TDD 步骤/验收/回滚） |
>
> **关联文档**：
> - [146：后台三件套改造评估与实施路线](./146-后台三件套改造评估.md)（**总纲**：阶段一的立项依据、决策记录、工作量与三阶段路线）
> - [138：文件管理重构](./138-文件管理重构.md)（门面 `file_service` + MD5 命名 + `file_bindings` 引用计数，本方案的改造基座）
> - [140：视频分片上传与断点续传](./140-视频分片上传与断点续传.md)（分片协议，§七 衔接改造）
> - [139：管线异常状态兜底与日志规范修正](./139-管线异常状态兜底与日志规范修正.md)（补偿/兜底任务的实现范式）
> - [72：Admin 备份管理增强](./72-Admin-备份管理增强.md)（文件备份语义需随本方案改写）
> - [73：测试体系引入 .env.test 实现环境隔离](./73-测试体系引入-env-test实现环境隔离.md)（测试继续 SQLite，假 backend 单测策略）

# 阶段一 KODO 对象存储细化方案

> 📋 **待执行**。前置条件：① 七牛 AK/SK + Bucket + Region 就绪；② 外链域名确定（**需已备案**，见 §十四）；③ 人类确认开工。上游路线见 [146 总纲](./146-后台三件套改造评估.md)。

## 一、范围

### 1.1 做什么

| # | 内容 |
|:-:|------|
| 1 | `StorageBackend` 抽象 + `local` / `kodo` 双实现 + 工厂分发 |
| 2 | `files` 表新增 `storage` / `storage_status` 两列 + Alembic 迁移 + 存量回填 |
| 3 | `config_registry` 注册 `storage.*` 配置项（新建 `storage` 分类） |
| 4 | **上传保留现状**：前端 → 后端本地落盘落库 → **同一请求内写对象存储** → 置 `SYNCED` → 返回 |
| 5 | **读取改外链**：后端响应层把 `rel_path` 转成对象存储绝对外链，前端零改动 |
| 6 | 分片上传（140）与分析管线派生产物接入 |
| 7 | 管理端：`scan` 状态扩展、清理双删 |
| 8 | **文件管理 S3 同步功能**（Admin 同步中心：存量搬迁 / 失败补偿 / 状态核对 / 进度） |
| 9 | 补偿重传、存量迁移脚本（与同步中心共用服务）、验收回归 |

### 1.2 不做什么（边界）

- ❌ 数据库迁移（阶段二 Supabase）、部署切换（阶段三 HF Space）
- ❌ 双写/多云冗余（[146 §3.4 (c)](./146-后台三件套改造评估.md) 明确不做）
- ❌ 小程序与**资源展示类**前端改造 —— 两端解析器已支持「绝对 URL 直通」（§6.5 代码为证）。**例外**：Admin 文件管理页有改动（同步中心弹层 + 状态列 + 筛选，见 §9.1），仅此一处
- ❌ bucket 公开读 —— 默认**私有 + 签名外链**（隐私数据 + `md5.ext` 可枚举）
- ❌ 读路径后端代理作为主通道 —— 仅作 `PENDING` 回落与鉴权下载（§6.4）

## 二、总体架构

```
                       ┌─ 路由层（upload/files/media/admin）── 零改动 ─┐
前端（小程序/Admin）     │                                              │
   ▲  上传：不变         ▼                                              ▼
   │ ┌──────────┐   file_service 门面（138：登记/秒传/引用计数）    响应层 url helper
   └→│ /upload/*│──→      │                                            │
      └──────────┘        ├─ file_store（路径/MD5/本地落盘，现状）      │ rel_path → 外链
                          └─ StorageBackend（新增）                    │ （§6.2 两态规则）
                                ├─ local_backend（现状等价实现）        ▼
                                └─ kodo_backend（boto3 S3 兼容）    前端直通分支原样使用
                                        │
                                        ▼
                              七牛 Kodo（私有 bucket）
```

**核心不变量**：`files` 表与 `rel_path` 永远是真相源；对象存储是**文件本体的归档地**，本地是**缓存与处理现场**。

## 三、数据模型变更

`app/models/file.py` 新增两列（Alembic `batch_alter_table`，SQLite 与阶段二 PG 双方言友好，**不引入新的 `sqlite_where`**）：

| 列 | 类型 | 默认 | 语义 |
|----|------|------|------|
| `storage` | `String(32)` | `"local"` | 本体位置：`local` / `kodo`（多源并存时可扩 `kodo:bucket名`，见 146 §3.4） |
| `storage_status` | `Integer` | `0` | 同步状态：`0=PENDING` 未同步 / `1=SYNCED` 已同步 / `2=FAILED` 失败待补偿 |

- 新增普通索引 `ix_files_storage_status`（补偿扫描用，双方言安全）
- **不变**：`rel_path`（同时作为对象键）、`(user_id, md5)` 部分唯一索引、`ref_count` 语义
- **迁移回填**：存量行 `storage='local'`、`storage_status=1`（本地即真相，视为已同步语义下的"无需上传"—— 另见 §九存量迁移：真正搬到 Kodo 后由迁移脚本改写为 `kodo`）

> `storage` 与 `storage_status` 缺一不可：前者说「在哪」，后者说「同步到没有」。只有位置列时，切配置 = 旧文件集体 404（146 §3.4 生死点）。

## 四、配置项（`config_registry` 注册）

**硬约束**：`config_service.get_config_value()` 对未注册 key 返回空串 → 全部必须进 `CONFIG_ITEMS`。新建分类（`Phase 78` 配置页会自动渲染）：

```python
{"key": "storage", "label": "对象存储", "description": "S3 兼容对象存储（七牛 Kodo）"}
```

| key | 类型 | 默认 | 说明 |
|-----|------|------|------|
| `storage.backend` | `select` | `local` | `local` / `kodo`；**即回滚开关** |
| `storage.endpoint` | `str` | `""` | S3 兼容 endpoint（如 `https://s3.<region>.qiniucs.com`） |
| `storage.region` | `str` | `""` | 区域 |
| `storage.bucket` | `str` | `""` | 桶名 |
| `storage.access_key` | `secret` | `""` | AK（Admin 页掩码，`mask_secret` 已有） |
| `storage.secret_key` | `secret` | `""` | SK |
| `storage.presign_ttl` | `int` | `7200` | 签名外链有效期（秒） |
| `storage.public_base_url` | `url` | `""` | 预留：将来启用公开读/CDN 直链时填 |
| `storage.local_retention` | `int` | `0` | `SYNCED` 后本地缓存保留天数，`0` = 永久保留（默认，见 §6.6） |

- 读取时机：**配置快照**——一次请求/一个管线开工时取一次，进行中不重读（146 §3.4 约束 4）

## 五、存储流程与状态机

### 5.1 三类文件的写路径

**路径 A：前端上传的小文件（头像 / 装备图 / 视频直传）**

```
前端 /upload/check 预检 → uploadFile 到后端      ← 流程零改动
  1. 落本地          file_store.write_bytes / move_into_place（现状）
  2. 秒传去重        find_by_md5()
                      ├ 命中 + SYNCED → 复用，结束（现状语义）
                      ├ 命中 + PENDING → 不落盘，补一次 put → SYNCED
                      └ 未命中 → 继续
  3. 落库            _new_file_record + flush   ★ storage=<当前backend>, storage_status=PENDING
  4. 写对象存储      kodo_backend.put(rel_path, 本地文件)   ← 用户确认的"上传完成之后再写"
  5. 更新状态        storage_status=SYNCED → commit
  6. 返回            响应字段已可给外链（§6.2）
```

> **无 404 窗口**：`put` 在响应之前同步完成 → 接口一返回，外链立即有效。`put` 抛错 → 事务回滚 + 保留 `PENDING` 行与本地文件，交补偿任务（§5.3）。

**路径 B：分片视频（140）**

```
open 会话 ★ manifest 写入 backend（会话全程用该快照）
 → pwrite_chunk 本地 chunk 暂存（现状）
 → complete：本地校验 → 落库(PENDING) → S3 一次 PUT（产物单文件 ≤ 数百 MB，无需 multipart）
            → SYNCED → 返回 file_id
 → chunk 清理：S3 同步成功后才 clear_chunks（现状 cleanup_expired_chunks 顺延触发）
```

**路径 C：分析管线派生产物（抽帧 / 骨架视频 / 裁剪片 / 报告）**

```
ffmpeg / mediapipe 写本地临时目录
 → register_batch()（121 预计算 MD5/size）★ 批量落库全为 PENDING
 → 逐个 put 到 S3 → 批量置 SYNCED
 → 再走现状清理（cleanup_intermediates / 采样帧删除 122/123）
```

> 与路径 A **同一条规则**，只是触发 put 的人不同（请求内 vs 管线内）；`file_service` 只有一处实现。

### 5.2 状态机

| 当前 | 事件 | 下一状态 | 动作 |
|:----:|------|:--------:|------|
| — | 落库 | `PENDING` | 位置列写当前默认 backend |
| `PENDING` | `put` 成功 | `SYNCED` | 响应可发外链 |
| `PENDING` | `put` 抛错 | `FAILED` | 记录日志（`{}` 占位符规范），等补偿 |
| `FAILED` | 补偿重传成功 | `SYNCED` | — |
| `SYNCED` | 读时发现对象 404 | `FAILED` | 告警 + 读侧回落代理（§6.4） |
| `SYNCED` | 业务删除 → 物理清理 | 行删除 | **双删**：同步删对象（§5.4） |

### 5.3 补偿任务（✅ Step 10 已落地）

**不引入常驻线程**（AGENTS 4.2 禁后台自启服务），复用 139 的兜底范式，三个触发点：

1. **启动时**：app 启动钩子扫一次 `PENDING/FAILED` 超时记录 —— `main.py` lifespan → `storage_sync_service.schedule_startup_compensation()`（`asyncio.to_thread` **一次性**任务，非 常驻线程；实现 `run_startup_compensation`，异常只记日志）
2. **请求内顺带**：上传接口成功后顺带尝试重传同用户的超时 `FAILED`（低频、无感）—— `upload.py` `_compensate_after_upload` 接入 avatar / gear-image / video 三端点，内部 `compensate_after_upload` 单批 5 条、异常绝不外抛
3. **Admin 手动**：文件管理页「S3 同步」中心一键补偿（见 §9.1，`scope=failed` 即批量重传，`@audit` 装饰 + 进度轮询）✅ Step 8

扫描条件：`storage_status IN (0,2) AND created_at < now - 60s`（给正常上传留窗口），单批上限 50 条防打爆。

> **统一实现**：`storage_sync_service.find_stale`（扫描）+ `compensate`（执行）—— `backend=local` 静默 no-op；已有同步任务在跑时返回 `conflict` 跳过（不与同步中心抢跑）；单条失败计数继续，不中断整批。

### 5.4 双删

- 软删（现状 `deleted_at`）：不动对象，只标记
- 物理清理（`cleanup_expired`，30 天后）：`db.delete(record)` **同时** `kodo_backend.delete(rel_path)`
- 对象删除失败 → 记日志继续删行（对象侧靠生命周期规则兜底），**不阻塞清理**

## 六、读路径与外链

### 6.1 两态响应规则

| 记录状态 | 响应给前端的值 | 前端行为 |
|---|---|---|
| `SYNCED` + `storage=kodo` | **绝对签名外链** | 直连七牛 CDN，不占后端带宽 |
| 其余（`local` / `PENDING` / `FAILED` / 无记录） | `rel_path` 原样 | 走现有后端代理，永不 404 |

### 6.2 响应层收口（一处实现，✅ Step 7 已按此落地）

**收口点**：`ApiResponse.model_post_init`（`app/schemas/common.py`）→ `storage.urls.rewrite_response_urls`。
任何 `ApiResponse(...)` 构造都会经过，前端零改动、路由零侵入。

```python
# app/services/storage/urls.py
def build_public_url_map(db, rel_paths) -> dict[str, str]:
    """rel_path → 绝对签名外链（一次 `IN` 批量查询；查不到的不入映射 → 回落代理）"""

def rewrite_response_urls(db, data) -> None:
    """响应树两趟遍历：先收集候选 rel_path → 一次批量映射 → 再原地改写"""
```

- **字段名注册表**（不按值猜测，避免误改普通字符串）：
  - `STRING_URL_FIELDS = {avatar_url, photo, video_url, thumb, rel_path}` — 值本身是路径
  - `PATH_BAG_FIELDS = {highlights, pose}` — 值内部装着路径（json_list / json_dict 逐层递归）
  - 与 `file_refs.FILE_REF_SPECS` 一一对应（§6.3 清单）
- 签发：`boto3 presigned GET`（七牛 S3 兼容），TTL 取 `storage.presign_ttl`
- **N+1 防护**：收集→**一次 `rel_path IN (...)` 批量查询**建映射→改写，一次响应只查一次 files
  （`TestQueryCount` 用 SQLAlchemy 事件断言 SELECT 命中 `FROM files` 恰好 1 次）
- **幂等**：改写后的值是绝对地址 → 第二趟 `is_candidate` 判否天然 no-op（序列化重复校验安全）
- **不刷库**：DB 永远存 `rel_path`，外链动态生成 → 存量数据零迁移

**请求级会话绑定（ContextVar）**：响应序列化不透传 DI context，故 `app/core/database.py`
定义 `current_session()` / `bind_request_db()`，由 `app/main.py` 的 **async** 应用级依赖
`_request_db_context` 绑定（覆盖未声明 `Depends(get_db)` 的路由，如 `/api/auth/me`）。

> ⚠️ **坑（Step 7 实测）**：绑定**不能**放在同步 `get_db` 里 —— FastAPI 对同步生成器依赖
> 用 `contextmanager_in_threadpool` 在**拷贝的 Context** 中执行，`ContextVar.set` 传不回
> 请求上下文，`reset(token)` 还会抛 `Token was created in a different Context`。
> 必须用 `async def` 依赖（同一 task 上下文进出）；同步端点经线程池 `copy_context()`
> 继承该值，只读场景足够。无绑定会话（后台任务/直接构造响应）时安全跳过。

- **异常兜底**：改写任何异常只 `log.exception`，绝不阻断响应返回

### 6.3 资源接入清单（✅ Step 0 已盘点，2026-10-26）

**核对基准**：`app/services/file_refs.py` 的 `FILE_REF_SPECS`（4 个 `business_type`、全部 `extractors` 字段）。**结论：下表覆盖全部注册字段，一一对应 ✅**

| # | 业务 | `file_refs` 注册字段 | 响应 schema / 构造点 | 前端消费点 | Step 7 接入方式 |
|:-:|------|---------------------|---------------------|-----------|----------------|
| 1 | user | `avatar_url`（column） | `UserResponse`（`from_attributes` + `model_validate`，auth.py **3 处**：login / me / update） | 小程序 `mine.vue`、`profile-edit.vue`；Admin `users/index.vue`、`system/event-logs.vue`（`avatarUrl`） | `field_serializer` + 批量 `url_map` |
| 2 | gear | `photo`（column，**dataURL 或相对路径**） | `GearResponse.model_validate`（gears.py **5 处**）+ Admin 装备详情 | 小程序 `gear/form.vue`（`resolveUploadUrl`，dataURL 分支短路）；Admin `gears/index.vue`（`fileUrl`） | 同上，**dataURL 分支不动** |
| 3 | analysis | `video_url`、`thumb`（column）<br>`highlights`（json_list）<br>`pose`（json_dict：`skeleton_video_url`/`skeleton_thumb`/`skeleton_cover` + `skeleton_frames` list） | `AnalysisResponse` ← **显式构造** `_to_response`（`analyses.py:75-88`、`admin/analyses.py:98-100`）**2 处** | 小程序 `report.vue`：`video_url`/`thumb`/`skeleton_video_url`/`skeleton_frames`（`imgSrc`→`resolveUploadUrl`）；Admin `analyses/index.vue`：`thumb`/`highlights`/`skeleton_video_url`（`fileUrl`）。`skeleton_thumb`/`skeleton_cover` 仅类型定义、暂无消费 | 两处 `_to_response` 传 `url_map` context；**列表/详情各批量查一次** |
| 4 | analysis_video_info | `derivatives`（json_list_of_dict: `rel_path`）<br>`source_file_id`/`playback_file_id` | **不在任何响应 schema**（仅登记/扫描/引用计数用） | 无（裁剪片经 Admin 文件页 `rel_path` 消费，已由 #5 覆盖） | **无接入点，不改** |
| — | 文件表自身 | `files.rel_path` | `AdminFileListResponse` / `AdminFileDetailResponse`（`admin_file.py` 2 处） | Admin `files/index.vue` 预览（`fileUrl`） | 列表/详情预览转外链；**下载仍走代理**（§6.4） |

**明确「不接入」的字段**（避免误改）：

| 字段 | 原因 |
|------|------|
| `AnalysisRequest.frame_urls` / `frames` | **请求入参**（后端读本地帧文件），非响应 |
| 路径参数 `/api/files/{path}`、`/api/media/{path}` | 输入即 `rel_path`，是代理端点本身（§6.4 保留） |
| 上传响应 `{"url": "avatars/..."}` | 前端**存库的是相对路径**（`uploadGearImage` 结果写入 `photo`），展示时才解析 → 上传响应无需改 |
| `Post` 模型 | 无文件字段（`date/platform/title/content/status`） |

**Step 0 关键发现（影响 Step 7 实现方式）**

1. **响应构造两条路**：除 `AnalysisResponse` 是显式 `_to_response` 外，其余全部走 Pydantic `model_validate(orm, from_attributes=True)` —— **没有逐字段的路由构造点** → 集中接入点是 **schema 层 `field_serializer` + 批量 `url_map` context**（`file_service.build_public_url_map(db, rel_paths)` 一次 `IN` 查询，满足 §6.2 N+1 防护）
2. **AGENTS 核心约束 4 已执行**：改共享响应模型前 grep 全量构造点 —— `UserResponse` 3 处、`GearResponse` 5 处、`AnalysisResponse` 2 处、`AdminFile*` 2 处；**只加 `field_serializer`，不动字段定义**
3. Pydantic `model_validate(obj, context=...)` 版本支持需在 Step 7 落地验证；不支持则降级为「路由层后处理两态字段」（构造点已盘点，改动可控）

### 6.4 保留后端代理的场景

1. **鉴权下载**：`GET /api/admin/files/{id}/download`（attachment + 权限），数据源改 S3 流式，不发外链
2. **`PENDING`/`FAILED` 回落**：见 §6.1
3. **Admin 免认证静态端点**（`/api/admin/system/files/*`）暂保留作兜底，列表预览优先外链

### 6.5 前端零改动论证（代码为证）

```ts
// miniapp/src/utils/index.ts  resolveUploadUrl
if (/^https?:\/\//.test(url) || url.startsWith("data:")) return url;   // ← 绝对外链直通
// admin/src/utils/fileUrl.ts  fileUrl / avatarUrl
if (isAbsolute(p)) return p                                            // ← 同上
```

后端返回绝对 URL → 走直通分支；返回相对路径 → 照旧拼后端。**两态并存 = 天然灰度与回滚开关**。

### 6.6 本地缓存策略（决策记录）

默认 `storage.local_retention=0`（永久保留本地副本）：

- 本地优先读 → 快；对象存储故障/欠费时业务不断
- 需要省磁盘时改配置按天清理（清后读侧自动回源 S3 并回填）
- 上传处理现场（管线临时目录）不受此配置影响，仍按现状即时清理

## 七、分片上传衔接（140）

| 时机 | 改动 |
|------|------|
| `open` | `manifest.json` 增写 `backend` 字段（会话开工时的配置快照，用于观测与一致性核对；真正 put 用 complete 时刻的快照，保证凭据最新） |
| `chunk` | 不变（本地 `data.bin` pwrite） |
| `complete` | 本地校验后：**单次 PUT → 落库（SYNCED）**；PUT 失败抛 `ChunkSyncError`（→503），**分片与 DB 均未被触碰、不返回 file_id**，保持可续传语义 |
| 清理 | `clear_chunks` 在 `register`（含同步）成功之后 |

## 八、分析管线衔接（119/121）

- 管线开工取**配置快照**（`storage.backend` + 凭据），56s 内不重读
- `register_batch` 后逐个 put；**任一 put 失败不使管线失败**（管线状态保持现状语义，文件交补偿）——但抽帧/播放短片等 139 定义的**致命步骤产物**除外：put 失败应按 139 fail-fast 打 `degraded` 标
- 本地清理（`cleanup_intermediates`、采样帧）**必须在 put 成功后**

## 九、管理端改造

### 9.1 文件管理 S3 同步功能（本阶段新增核心能力，✅ Step 8-9 已落地）

**定位**：Admin 文件管理页（`admin/src/views/files/index.vue`）新增「S3 同步」中心，覆盖三类诉求 —— **存量搬迁**（`storage=local` → `kodo`）、**失败补偿**（`FAILED` 重传）、**状态核对**（统计与单条同步）。

- 与 §五 的关系：上传/管线的**在线自动同步**照旧走 §五（请求内/管线内），本功能负责**存量与补偿**，两者互补
- 与 138 的关系：文件管理页/表格/筛选已成体系，本功能是其工具栏能力扩展

**后端端点**

| 端点 | 入参 | 返回 | 说明 |
|------|------|------|------|
| **新增** `POST /api/admin/files/sync` | `{scope: "pending"\|"failed"\|"local"\|"selected", file_ids?: [], dry_run?: bool, force?: bool}` | `{queued, skipped, estimate_bytes, task_id}` | 入队执行；`dry_run=true` **只统计不改动**（预览影响条数/字节）；`force` 对已 `SYNCED` 也重传（HEAD 核对用）；`@audit(action="SYNC")` |
| **新增** `GET /api/admin/files/sync-status` | — | `{total, synced, pending, failed, local_only, running, progress:{done,total,failed}, last_sync_at}` | 统计卡片 + 进度轮询 |
| **新增** `POST /api/admin/files/sync/{file_id}` | — | 单条同步结果 | 表格行内按钮；`@audit(action="SYNC")` |

**实现要点**

1. **单一服务源**：`storage_sync_service.sync_records(records, force=False)` —— CLI 脚本 `scripts/migrate-files-to-kodo.py` 只是它的入口，**在线同步与存量迁移共用一套逻辑**
2. **幂等**：`SYNCED` 默认跳过（天然断点续传）；逐条 `PUT` + 更新状态，单条失败计数继续，**不中断整批**
3. **批量**：游标分页取 `storage=local` 或 `storage_status != SYNCED`，单批 50 条；长任务走 `BackgroundTasks`（119 已有先例，**不引入常驻线程**，守 AGENTS 4.2）
4. **并发防重**：进程内 `running` 标志（当前单 worker 部署）→ 进行中再触发返回 409；前端 `useActionLock` 二次防护（Phase 68）
5. **进度**：service 内存计数，`sync-status` 读取；重启归零可接受（幂等可重跑）
6. **边界**：**只上传不删本地**（`storage.local_retention` 独立生效）；`backend=local` 时端点返回 400「未启用对象存储」

**前端（Admin 文件页）**

| 位置 | 内容 |
|------|------|
| 工具栏 | 「S3 同步」按钮 → 弹层（复用自定义大弹窗，方案 70 先例） |
| 弹层 | 统计卡片（`total/synced/pending/failed/local_only`）+ 范围选择（待同步 / 失败 / 全部本地 / 选中项）+ `dry_run` 预览（条数 + 总字节）+ 执行按钮 + **进度条轮询** `sync-status`（参考 Phase 74 轮询模式，任务结束停止） |
| 列表 | 新增两列：`storage`（local/kodo）徽标 + 同步状态图标；筛选器支持按 `storage_status` 过滤 |
| 防护 | `useActionLock` 防重复提交 + 全局 Loading（Phase 68） |

> **为什么必须做在线功能而不是只有脚本**：阶段一验收要看到「`local_only → 0`」的可观测结果；脚本只能由运维在服务器上跑，在线同步中心让管理员自助执行、看进度、查失败，且是阶段二数据迁移前的**文件侧体检工具**。

### 9.2 其他管理端改造

| 端点 | 改动 |
|------|------|
| `POST /scan` | 五态扩展：新增 `pending_sync`（存量未搬迁 / PENDING / FAILED）；`missing` 重定义为「DB 有而**对象存储无**」（一次 `iter_keys` 全量列举核对，Admin 手动触发，不做定时全扫；列举失败则跳过核对不误报）✅ Step 8 |
| `POST /cleanup`、`/cleanup-orphans` | 走 §5.4 双删（对象删除失败只记日志，不阻塞清理）✅ Step 8 |
| `GET /{id}/download` | Range 数据源换 S3（透传 Range → 206），端点与鉴权不变 |
| 列表/统计/软删/批量删/注册/migrate-md5/repair | **零改动**（纯 DB） |
| 备份（72） | 文件本体备份责任移交七牛侧（可选 bucket 版本控制）；方案 72 文档在本阶段完成后同步修订 |

**同步端点三件套（✅ Step 8 已落地，单一服务源 `app/services/storage_sync_service.py`）**

| 端点 | 行为 |
|------|------|
| `GET /sync-status` | 五类计数（total/synced/pending/failed/local_only，与 DB 实际一致）+ `running`/`progress`/`last_sync_at`；`backend=local` → 400 |
| `POST /sync` | `{scope, file_ids, dry_run, force}`：`dry_run` 只统计零改动；正式执行 `BackgroundTasks` 跑批立即返回 `task_id`；执行中重复触发 → **409**（进程内 `RUN_STATE`）；`@audit(action="SYNC")` |
| `POST /sync/{id}` | 单条同步：本地缺失 → 状态 `FAILED` 且 HTTP 200（可补偿，不 500）；未知 id → 404；`@audit` |

**存量迁移（✅ Step 10 已落地）**：CLI 脚本 `scripts/migrate-files-to-kodo.py` 作为 `storage_sync_service` 的命令行入口（复用 138 一键迁移先例），支持 `--scope/--dry-run/--force/--file-ids`，与同步中心行为完全一致；本地副本去留仍由 `local_retention` 决定。

## 十、TDD 实施步骤

| Step | 内容 | 类型 | 验证 |
|:----:|------|:----:|------|
| 0 | 盘点响应字段清单，回填 §6.3 表 | 调研 | 清单与 `file_bindings.field` 一致 |
| 1 | `StorageBackend` 接口 + **内存假 backend** 单测（put / head / open_range / delete / presign） | 🔴 RED | `pytest -m fast` 失败 |
| 2 | `local_backend`（封装现状行为）+ `kodo_backend`（boto3）+ 工厂 | 🟢 GREEN | 单测通过 |
| 3 | `config_registry` 新增 `storage` 分类 + 9 项配置（含 secret 掩码） | 🟢 | 配置页渲染 + `pytest tests/.../config*` |
| 4 | `files` 两列 Alembic 迁移 + 索引 + 回填默认值 | 🟢 | `alembic upgrade head` 干净可回滚 |
| 5 | 路径 A 接线：`register` 后 put + 状态流转 + 失败回退 | 🟢 | 新增上传状态用例 |
| 6 | 路径 B/C：分片 manifest 绑定 + `register_batch` 后 put | 🟢 | 分片/管线用例 |
| 7 | 响应层 `to_public_url` + 批量查询 + §6.3 各资源接入 | 🟢 | 两态响应用例（外链 / 回落） |
| 8 | 管理端：scan 扩展 + 双删 + 同步端点骨架（`sync` / `sync-status` / `sync/{id}`） | ✅ 已完成 | 2026-10-26 | 22 例（scan 两态 / 双删 / 端点门禁与统计 / dry_run / 409 / 单条）；fast 333 passed |
| 9 | **文件管理 S3 同步功能**：`storage_sync_service` + `dry_run`/`force`/防并发 + Admin 文件页同步弹层/状态列/筛选/进度轮询 | ✅ 已完成 | 2026-10-26 | 服务/端点见 Step 8；本步为前端接入 + 列表两列与筛选；fast 336 passed + admin `vue-tsc`/build 通过 |
| 10 | 补偿任务三触发点 + 存量迁移 CLI（共用 `storage_sync_service`） | ✅ 已完成 | 2026-10-26 | `tests/test_storage_compensation.py` 19 例 + 上传端点集成 1 例；`scripts/migrate-files-to-kodo.py`；fast 355 passed |
| 11 | 回归 + 真机 | ✅ 回归完成 | 2026-10-26 | 全量 874 passed；真机 3 项待 P0 域名/凭据（§十一 ⏳） |

每 Step 结束跑 AGENTS 4.3 门禁：`cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast`。

## 十一、验收清单

**门禁（✅ Step 11 已实跑，2026-10-26）**：`ruff check/format` 干净 + `pytest -m fast` **355 passed** + 全量 `pytest -n auto` **874 passed, 0 failed**（含修复预存失败 `test_forehand_video_processed`）；`admin type-check + build` ✅、`miniapp type-check + build:mp-weixin` ✅、`pnpm docs:build` ✅。

| # | 用例 | 期望 | 状态 |
|:-:|------|------|:----:|
| 1 | 上传头像/装备图 | 响应字段为绝对外链，浏览器/小程序直连可开 | 🤖 两态响应/回落已自动化；**绝对外链待线上**（需七牛凭据） |
| 2 | 秒传命中（同 MD5 二次上传） | 不重复上传，直接复用 `SYNCED` | 🤖 `test_file_storage_sync` |
| 3 | 分片视频上传 + 断点续传 | complete 后 `SYNCED`，外链可播 | 🤖 状态机已自动化；外链播放待线上 |
| 4 | 视频拖动进度条 | 206 Range 正常（外链侧由七牛保证） | ⏳ 待线上（七牛侧保证） |
| 5 | 模拟 `put` 失败 | 记录落 `FAILED`、请求报错可重试、补偿后转 `SYNCED` | 🤖 Step 5 + `test_storage_compensation` |
| 6 | `PENDING` 记录的读 | 响应返回相对路径，走代理正常显示（**不 404**） | 🤖 `test_response_urls` |
| 7 | 文件删除 | DB 软删 → 过期清理时对象同步删除 | 🤖 `TestDoubleDelete` |
| 8 | Admin `scan` | `pending_sync` / `missing` 状态正确 | 🤖 `TestScanStorageStates` |
| 9 | Admin 列表预览 + 下载 | 预览走外链、下载走代理 206 | 🤖 代理 206 已自动化；外链预览待线上 |
| 10 | `storage.backend=local` 切回 | 全部读写本地，前端无感知（回滚验证） | 🤖 local 档位多处用例 |
| 11 | 真机小程序 | 头像/装备图/视频外链加载正常（**downloadFile 合法域名已配**） | ⏳ **待人类**（P0：已备案外链域名） |
| 12 | S3 同步中心统计 | `total/synced/pending/failed/local_only` 与 DB 实际一致；`backend=local` 时端点 400 | 🤖 `TestSyncStatus` + `TestSyncEndpointGate` |
| 13 | `dry_run` 预览 vs 实际执行 | `dry_run=true` 返回条数/字节但**零数据改动**；正式执行后 `local_only` 按预期下降 | 🤖 `TestSyncRun` |
| 14 | 同步并发与失败 | 执行中重复触发返回 409（前端按钮锁定）；单条 `PUT` 失败计入 `failed` 且不中断整批，`scope=failed` 可重传 | 🤖 409 / 单条失败不中断 / 补偿重传三组用例 |

> **验收结论**：14 项中 **11 项已自动化覆盖**（🤖），**3 项依赖外部条件**（⏳：#4 外链 206、#9 外链预览、#11 真机）——三者都要求七牛凭据 + 已备案外链域名（P0，人类提供）。凭据/域名就位后按本表逐项线上复核即可。

## 十二、回滚方案

1. **配置回滚（秒级）**：`storage.backend=local` → 读写全部回本地，前端因两态规则自动回落代理
2. **代码回滚**：阶段一独立分支，`git revert` 不影响阶段二/三
3. **数据**：对象与 `storage` 字段保留（回滚后读路径不看它们）；本地副本全程保留 = 随时可回

## 十三、依赖与工作量

| 项 | 说明 |
|----|------|
| 硬前置 | 七牛 AK/SK + Bucket + Region；**已备案外链域名** CNAME 到七牛 CDN |
| 软前置 | 当前生产（魔搭）稳定可回归 |
| 工作量 | Step 0-2 约 1.5 人日；Step 3-6 约 2 人日；Step 7-8 约 1 人日；**Step 9 同步功能约 1~2 人日**；Step 10-11 约 1.5~2 人日 → **合计 7~10 人日** |

> 相对 [146 §五](./146-后台三件套改造评估.md) 原估（4~7）上浮：外链响应层转换面较宽 + 文件管理 S3 同步功能（146 v1.4.0 已同步为 7~10）。

---

## 十七、附录：七牛云 KODO 配置标识符与获取路径

### 十七.1 七牛云配置值说明

| 配置项 | `STORAGE_` | 说明 | 目标值示例 |
|--------|------------|------|------------|
| 对象存储后端 | `BACKEND` | `local`（本地） / `kodo`（七牛） | `kodo` |
| 区域标识符 | `REGION` | Region ID，与 Endpoint 匹配 | `cn-east-2` |
| S3 协议 Endpoint | `ENDPOINT` | 用于 S3 兼容 API（boto3） | `s3.cn-east-2.qiniucs.com` |
| 存储桶名称 | `BUCKET` | 创建时指定的全局唯一名称 | `tennis-diary` |
| 访问密钥 | `ACCESS_KEY` | AccessKey（AK） | `AKxT...` |
| 密钥 | `SECRET_KEY` | SecretKey（SK） | `SKyZ...` |
| 公共域名 | `PUBLIC_BASE_URL` | 已备案 CDN 域名，用于外链展示 | `https://file.tennisdiary.cn` |
| 签名有效期 | `PRESIGN_TTL` | 签名链接有效期（秒） | `2592000` |

### 十七.2 区域标识符（Region ID）清单

| 存储区域 | Region ID | 说明 |
|----------|-----------|------|
| 华东-浙江 | `z0` | 旧称，兼容 |
| 华东-浙江2 | `cn-east-2` | 推荐 |
| 华北-河北 | `z1` | 旧称，兼容 |
| 华南-广东 | `z2` | 旧称，兼容 |
| 北美-洛杉矶 | `na0` | 旧称，兼容 |
| 亚太-新加坡（原东南亚） | `as0` | 旧称，兼容 |
| 亚太-河内 | `ap-southeast-2` | 存量运营 |
| 亚太-胡志明 | `ap-southeast-3` | 存量运营 |

### 十七.3 S3 协议 Endpoint 清单

| Region ID | S3 协议 Endpoint | 说明 |
|-----------|------------------|------|
| `z0` / `cn-east-1` | `s3.cn-east-1.qiniucs.com` | 华东-浙江 |
| `cn-east-2` | `s3.cn-east-2.qiniucs.com` | 华东-浙江2 |
| `z1` / `cn-north-1` | `s3.cn-north-1.qiniucs.com` | 华北-河北 |
| `z2` / `cn-south-1` | `s3.cn-south-1.qiniucs.com` | 华南-广东 |
| `na0` / `us-north-1` | `s3.us-north-1.qiniucs.com` | 北美-洛杉矶 |
| `as0` / `ap-southeast-1` | `s3.ap-southeast-1.qiniucs.com` | 亚太-新加坡 |
| `ap-southeast-2` | `s3.ap-southeast-2.qiniucs.com` | 亚太-河内 |
| `ap-southeast-3` | `s3.ap-southeast-3.qiniucs.com` | 亚太-胡志明 |

> ⚠️ **禁止错误**：不要用 `up-*.qiniup.com`（上传域名）或 `iovip-*.qiniuio.com`（下载域名），必须用 S3 协议的 `s3.*.qiniucs.com`

### 十七.4 CNAME 指向域名清单

| 存储区域 | CNAME 指向 | 用途 |
|----------|-----------|------|
| 华东-浙江 | `iovip.qiniuio.com` | 域名解析 |
| 华东-浙江2 | `iovip-cn-east-2.qiniuio.com` | 域名解析 |
| 华北-河北 | `iovip-z1.qiniuio.com` | 域名解析 |
| 华南-广东 | `iovip-z2.qiniuio.com` | 域名解析 |
| 北美-洛杉矶 | `iovip-na0.qiniuio.com` | 域名解析 |
| 亚太-新加坡 | `iovip-as0.qiniuio.com` | 域名解析 |
| 亚太-河内 | `iovip-ap-southeast-2.qiniuio.com` | 域名解析 |
| 亚太-胡志明 | `iovip-ap-southeast-3.qiniuio.com` | 域名解析 |

### 十七.5 官方文档查询路径

| 内容 | 官方文档链接 |
|------|--------------|
| 存储区域和访问域名 | [存储区域_产品简介_对象存储](https://developer.qiniu.com/kodo/1671/region-endpoint-fq) |
| 服务域名（S3 协议）使用指南 | [服务域名_使用指南_对象存储](https://developer.qiniu.com/kodo/4088/s3-access-domainname) |
| 基本概念（创建存储桶） | [基本概念_产品简介_对象存储](https://developer.qiniu.com/kodo/3978/the-basic-concept) |
| 绑定源站域名 | [绑定源站域名_使用指南_对象存储](https://developer.qiniu.com/kodo/8622/dev-the-binding-source-domain-name) |

### 十七.6 推荐配置（国内用户）

```env
STORAGE_BACKEND=kodo
STORAGE_REGION=cn-east-2
STORAGE_ENDPOINT=s3.cn-east-2.qiniucs.com
STORAGE_BUCKET=tennis-diary
STORAGE_ACCESS_KEY=你的AK
STORAGE_SECRET_KEY=你的SK
STORAGE_PUBLIC_BASE_URL=https://file.tennisdiary.cn
STORAGE_PRESIGN_TTL=2592000
```

### 十七.7 配置值获取步骤

1. **登录七牛云控制台**
2. **创建存储桶**：
   - 空间名称：`tennis-diary`（或其他唯一名称）
   - 区域：选择 `华东-浙江2`（推荐）或 `华东-浙江`
3. **获取密钥**：
   - 点击头像 → **密钥管理**，记录 `AccessKey` 和 `SecretKey`
4. **绑定域名**：
   - 悬停于存储桶 → **域名管理** → 添加已备案域名（如 `file.tennisdiary.cn`）
5. **填写 `.env`**：使用上述推荐配置，替换实际值
6. **重启后端**：`cd server && uv run uvicorn app.main:app --reload`

---

💡 **提示**：以上清单会随七牛云官方文档更新而调整，建议开发时同时查阅官方文档获取最新信息。

## 十四、风险与未决

| 级别 | 项 | 处理 |
|:----:|---|------|
| **P0** | **外链域名备案**：小程序 `<image>/<video>` 走 `downloadFile` 合法域名，必须已备案；七牛测试域名不可用 | 归入决策 2「域名在项目外配置」范围，**开工前确认**，备案周期 2~4 周 |
| **高（已修 ✅）** | **本地门禁在 Windows 失败**：`file_store.pwrite_chunk` 用 `os.pwrite`（仅 POSIX），本机 win32 下 `tests/test_file_facade_chunks.py` **18 failed / 207 passed**（Step 0 基线实测，2026-10-26）；CI（Linux）不受影响 | **Step 0.5 已修**：抽出 `_pwrite` —— POSIX 走 `os.pwrite`，Windows 回退 `os.lseek + os.write` 并循环写满（fd 每次调用独享，语义等价）；`pytest -m fast` 225 passed 全绿。`fix` 提交（根 package.json 1.86.4 + CHANGELOG） |
| 高 | 七牛 S3 兼容 API 差异（presign / Range / PUT） | Step 1 用真实凭据先做一次连通性 spike，再写实现 |
| 中 | 响应层 N+1 查询 | §6.2 强制批量 `IN` 查询，列表接口加用例 |
| 中 | 签名 TTL（2h）与分享卡片 | 卡片为 Canvas 即时生成，无长有效期问题；长链场景改走代理 |
| 中 | 上传链路跨境（后端在 HF 境外 ↔ 七牛境内） | **阶段一在魔搭（境内）实施，无此问题**；阶段三 HF 切换时复评（届时外链读不受影响，仅写入变慢） |
| 低 | 备份语义变化（72） | 本阶段完成后修订方案 72 |

## 十五、执行进度

| Step | 内容 | 状态 | 日期 | 备注 |
|------|------|:----:|:----:|------|
| 0 | 响应字段盘点 | ✅ 已完成 | 2026-10-26 | 与 `file_refs` 注册表一致；5 类接入点 + 4 项不接入；发现见 §6.3 |
| 0.5 | Windows `os.pwrite` 兼容修复（基线 18 failed） | ✅ 已完成 | 2026-10-26 | `_pwrite` 双路径；`pytest -m fast` 225 passed 全绿（1.86.4） |
| 1 | `StorageBackend` 契约测试（put/head/open_range/delete/presign/iter_keys） | ✅ 已完成 | 2026-10-26 | `tests/services/test_storage_backend.py` 38 例 🔴 RED |
| 2 | `base`/`memory`/`local`/`kodo`/`factory` + `boto3` 依赖 | ✅ 已完成 | 2026-10-26 | 同文件 38 例 🟢（225→263 passed）；`kodo` 客户端懒构造 |
| 3 | `storage` 分类 + 9 项配置 + `Settings.STORAGE_*` | ✅ 已完成 | 2026-10-26 | `tests/core/test_storage_config_registry.py` 9 例；顺带修正 `ConfigItemDef.default` 的 `0`/`bool` 语义 |
| 4 | `files` 两列 + `ix_files_storage_status` + 迁移 `c7a147f0b3d5` | ✅ 已完成 | 2026-10-26 | `tests/test_migrations_147.py` 6 例；真实链 upgrade→downgrade→upgrade 验证 |
| 5 | 路径 A 接线：`register` 落库后 put + 状态流转 + 失败回退 | ✅ 已完成 | 2026-10-26 | `tests/test_file_storage_sync.py` 7 例；`sync_to_storage` + 快照实例缓存；fast 门禁 285 passed |
| 6 | 路径 B/C：分片 manifest 绑定 + `register_batch` 后 put | ✅ 已完成 | 2026-10-26 | `register_batch` 逐条同步单条失败不中断；`complete` **先 pre-put 再落库**（失败抛 `ChunkSyncError`→503，分片与 DB 未动可续传）+ `manifest["backend"]` 快照；fast 门禁 290 passed |
| 7 | 响应层外链 | ✅ 已完成 | 2026-10-26 | `storage.urls` 收口 + §6.3 全资源接入；fast 311 passed（新增 21 例） |
| 8 | 管理端 scan/双删 + 同步端点骨架 | ✅ 已完成 | 2026-10-26 | `test_files_sync.py` 22 例；`storage_sync_service` 单一服务源；fast 333 passed |
| 9 | **文件管理 S3 同步功能**（服务 + Admin 页面） | ✅ 已完成 | 2026-10-26 | 列表补 `storage`/`storage_status` 两列与筛选；Admin 同步弹层/状态列/筛选/进度轮询/`useActionLock`；`test_files_sync.py` 25 例，fast 336 passed + admin build ✅ |
| 10 | 补偿三触发点 + 迁移 CLI | ✅ 已完成 | 2026-10-26 | `find_stale`/`compensate` + lifespan 启动一次性任务 + 三上传端点顺带补偿 + `migrate-files-to-kodo.py`；fast 355 passed、全量 873 passed |
| 11 | 回归与真机验收 | ✅ 回归完成 / ⏳ 真机待办 | 2026-10-26 | 全量 `pytest -n auto` **874 passed, 0 failed**（修复预存 `test_forehand_video_processed` 过期断言：`frame_urls` 为 router 层字段，改断言服务层 `frame_paths`）；admin/miniapp type-check+build、`docs:build` 全绿；§十一 14 项 → 11 项自动化、3 项待线上（P0 域名 + 七牛凭据） |
