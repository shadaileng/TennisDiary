> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 75-B2-Admin |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-13 |
> | 对应功能/内容 | Admin 同步 AI 网关三件套：分析报告管理增强 + AI 网关状态监控 + Admin 静态文件服务 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-13 | v1.1.0 | 实施完成：后端详情返回完整六维报告 + ai-status/ai-connect/files 三端点（19 新增测试，全量 202 passed）；Admin 分析页模式/封面列 + 六维报告弹窗 + 健康页 AI 网关卡片，pnpm build 通过 |
> | 2026-08-13 | v1.0.0 | 初版（承接 [75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) 的后台管理侧） |
>
> **关联文档**：[75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) · [43-B2 后台管理 API 总纲](./43-B2-后台管理API总纲.md) · [46-B2-3 系统监控 API](./46-B2-3-系统监控API.md) · [52-Admin-5 数据管理](./52-Admin-5-数据管理.md) · [53-Admin-6 系统监控](./53-Admin-6-系统监控.md)

# Admin 同步 AI 网关功能

## 一、背景与目标

[75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) 规划了服务端 AI 评分 / 视频抽帧 / 姿态推理三大能力，其中「报告落库」约定分析报告持久化为六维 JSON。本方案补齐 **Admin 后台管理端**对这三件套的同步支撑：

| 目标 | 说明 |
|------|------|
| 分析报告管理增强 | Admin 分析列表展示模式/封面；详情弹窗渲染完整六维报告（评分条/节奏/亮点/改进建议/封面与高光帧） |
| AI 网关状态监控 | 健康检查页新增「AI 网关」卡片，探测 AI Key / ffmpeg / MediaPipe / 姿态模型四项状态，支持 AI 连通性测试 |
| Admin 静态文件服务 | 新增 `GET /api/admin/system/files/{path}`，供 Admin 渲染 `thumb` / `highlights` 图片 |

## 二、现状与差距分析

### 2.1 现状（已完成的基础）

| 层 | 现状 | 备注 |
|---|---|---|
| 后端模型 | `Analysis` 已有 `report`(JSON) / `thumb` / `highlights` 字段 | 75-B2 规划的 `AnalysisReport` 无需新建表，直接复用 `analyses.report` 存完整六维 JSON |
| 后端路由 | `/api/admin/analyses` 已有 list / detail / delete | 详情接口返回字段过少，缺完整报告 |
| 后端配置 | `config.py` 已有 `AI_API_KEY / AI_BASE_URL / AI_MODEL` | AI 配置项已就位，可做状态探测 |
| 后端 Schema | `AnalysisAdminResponse` 缺 `report / thumb / highlights` | 详情页无法展示六维报告 |
| Admin 前端 | 分析页列表 + 简单详情弹窗（只有 date/kind/score/summary） | 详情弹窗直接用行数据，未调用详情接口 |
| 系统监控 | health / stats 无 AI 网关状态 | 无法看到三件套运行状况 |

### 2.2 关键差距（本次补齐）

1. **后端详情接口**不返回完整报告 JSON → Admin 看不到六维评分/节奏/亮点/改进建议；
2. **Admin 分析页**列表缺 `mode`（single/full）、缩略图；详情弹窗无法渲染六维报告；
3. **系统监控**无 AI 网关三件套状态探测（ffmpeg / MediaPipe / 姿态模型 / AI Key 配置）；
4. **Admin 前端** `Analysis` 类型缺 `mode / report / thumb / highlights` 字段；
5. **静态文件访问**：Admin 端无通用静态文件端点，`thumb / highlights` 图片无法渲染（仅备份下载走 `FileResponse`）。

## 三、详细方案

### Part A：分析报告管理增强（核心）

#### A1. 后端 Schema 扩展（`server/app/schemas/admin.py`）

- `AnalysisAdminResponse` 保持不变（列表精简）；
- **新增** `AnalysisDetailAdminResponse`（继承列表响应 + 完整报告字段）：

```python
class AnalysisDetailAdminResponse(AnalysisAdminResponse):
    report: dict | None = None          # 后端 json.loads(report) 后返回结构化对象
    thumb: str | None = None            # 封面帧路径/URL
    highlights: list[str] | None = None  # 高光帧路径数组
```

#### A2. 后端详情接口增强（`server/app/routers/admin/analyses.py`）

- `get_analysis` 返回类型改为 `AnalysisDetailAdminResponse`；
- 解析 `report` / `highlights` 两处 JSON（`try/except`，兼容历史脏数据，解析失败返回 `None`）；
- 复用 `_enrich_analysis`（补 user 信息）。

#### A3. Admin 前端 API 类型扩展（`admin/src/api/analyses.ts`）

- 新增 `DimensionScore`、`AnalysisReport` 类型（与参考版 `types.ts` 对齐）：

```typescript
export interface DimensionScore {
  name: string
  score: number
  comment: string
}
export interface AnalysisReport {
  score: number
  summary: string
  ntrp?: string
  dimensions: DimensionScore[]
  rhythm: string
  strengths: string[]
  improvements: { issue: string; advice: string }[]
}
```

- `Analysis` 增加 `mode / report? / thumb? / highlights?`；
- 新增 `getAnalysisDetail(id)`（或复用现有 `getAnalysis` 并把返回类型改为详情类型）。

#### A4. 分析列表页增强（`admin/src/views/analyses/index.vue`）

- 列表列：
  - 增加「模式」列（`single`→单次挥拍 / `full`→综合分析，Badge 显示）；
  - 增加「封面」列：`row.thumb` 有值时显示缩略图（`<img class="h-10 w-16 object-cover rounded">`），无值时 `--`；
- 详情弹窗改造：
  - 「查看」按钮改为调用 `getAnalysisDetail(id)` 拉取完整报告，而非用行数据；
  - 弹窗渲染：
    - 头部：总分（大字 + 颜色分级）+ NTRP 徽章 + kind/mode/date；
    - `summary` 一句话总结；
    - **六维评分条**：遍历 `report.dimensions`，每项 name + 进度条（score/100）+ comment；
    - **节奏观察**：`report.rhythm`；
    - **亮点**：`report.strengths` 列表（✓ 绿色）；
    - **改进建议**：`report.improvements` 每条 `issue`（红）→ `advice`（灰，可加"建议"前缀）；
    - **封面/高光帧**：`thumb` 大图预览 + `highlights` 缩略图行（走 Part E 静态文件服务）；
  - 兼容：`report` 可能是字符串（历史数据），前端 `JSON.parse` 兜底。

### Part B：AI 网关状态监控（新增）

#### B1. 后端探测端点（`server/app/routers/admin/system.py`）

新增 `GET /api/admin/system/ai-status`（权限 `system:health`），返回三件套运行状况：

| 字段 | 探测方式 |
|---|---|
| `ai.configured` | `bool(settings.AI_API_KEY)` |
| `ai.model` / `ai.base_url` | `settings.AI_MODEL` / `settings.AI_BASE_URL`（域名非机密，直接返回） |
| `ai.key_masked` | `sk-****{末尾4位}`，无 Key 返回 `""` |
| `ffmpeg.available` / `ffmpeg.version` | `shutil.which("ffmpeg")` + `subprocess ffmpeg -version` 首行 |
| `mediapipe.available` | `importlib.util.find_spec("mediapipe")` |
| `pose_model.available` / `path` | 检查姿态模型文件是否存在（配置化路径） |
| `summary.ok` / `summary.missing` | 汇总：AI Key / ffmpeg / mediapipe / 模型 四者缺哪些 |

> `AI_API_KEY` 只返回掩码，不暴露明文；不做「修改 AI 配置」（Key 仅存服务端 `.env`，Admin 远程无法安全写入并热生效）。

#### B2. AI 连通性测试端点

新增 `GET /api/admin/system/ai-connect`（权限 `system:health`）：服务端代理 `GET {AI_BASE_URL}/models`，仅验证 Key 有效性，**不耗 token**，成功/失败均返回结构化结果供前端反馈。

#### B3. 健康检查页增强（`admin/src/views/system/health.vue`）

- 新增「AI 网关」卡片：
  - AI 评分：已配置（Key 掩码显示）/ 未配置；
  - 模型名 / Base URL；
  - ffmpeg：可用（版本）/ 不可用（提示 75-B2 风险与 `imageio-ffmpeg` 兜底）；
  - MediaPipe：可用 / 不可用；
  - 姿态模型：存在 / 缺失；
  - 汇总 Badge：全部就绪（绿）/ 部分缺失（黄，列出缺失项）；
- 「刷新状态」按钮同时刷新健康检查与 AI 网关两卡；
- 「测试 AI 连接」按钮调用 `/ai-connect`，成功/失败均有 UI 反馈；
- `admin/src/api/system.ts`：新增 `AiStatus` 类型与 `getAiStatus()`、`testAiConnect()`。

### Part C：权限 / 路由 / 菜单

- **无需新增权限**：分析详情复用 `analyses:view`（43-B2 已定义），AI 状态复用 `system:health`；
- **无需新增路由/菜单**：全部收敛到现有「分析报告」页 + 「系统监控 → 健康检查」页。

### Part D：文档

本方案文档（📋 待执行）+ 同步 `docs/README.md` 文档一览 / 执行进度 + `docs/.vitepress/config.mts` 侧边栏（归入「Phase B2（AI 网关三件套）」分组）。

### Part E：Admin 静态文件服务（回应"静态文件服务"确认）

#### E1. 后端新端点（`server/app/routers/admin/system.py`）

新增 `GET /api/admin/system/files/{filename:path}`：

| 设计点 | 说明 |
|---|---|
| 鉴权 | `get_current_admin`（管理端本可见全部数据，无需按用户归属校验） |
| 路径防护 | 复用 `_resolve_safe_path` 同款逻辑（`normpath` + 限定在 `UPLOAD_DIR` 内，越界 404），本次直接内聚在 admin/system.py，改动最小 |
| 媒体类型 | 复用 jpg/png/webp/gif/mp4 映射（Admin 端无此表，内联一份；或用 `mimetypes.guess_type` 兜底） |
| 返回 | `FileResponse`，文件不存在返回 404 |
| 用途 | Admin 前端渲染 `Analysis.thumb`（封面）与 `highlights`（高光帧）的 `<img src="/api/admin/system/files/xxx.jpg">` |

#### E2. 前端对接

- Admin `analyses/index.vue` 中所有图片 URL 统一拼接 `const fileUrl = (p) => p ? \`/api/admin/system/files/${p}\` : ''`；
- axios 已配 baseURL（生产走反代），`<img>` 直接填完整路径即可；
- `thumb / highlights` 字段语义：若未来存的是绝对 URL（对象存储），`fileUrl` 判断 `http` 开头则原样返回，保持兼容。

## 四、文件改动清单

**后端（server/）**

| 文件 | 改动 |
|---|---|
| `server/app/schemas/admin.py` | 新增 `AnalysisDetailAdminResponse`（report 对象 / thumb / highlights） |
| `server/app/routers/admin/analyses.py` | 详情接口返回完整报告（解析 report/highlights JSON，容错历史脏数据） |
| `server/app/routers/admin/system.py` | ① 新增 `GET /api/admin/system/ai-status`（AI Key 掩码 / ffmpeg / MediaPipe / 姿态模型探测）；② 新增 `GET /api/admin/system/files/{path}` 静态文件服务（路径防护 + 媒体类型映射）；③ 新增 `GET /api/admin/system/ai-connect`（AI 连通性测试，代理 `{AI_BASE_URL}/models`，不耗 token） |
| `server/tests/` | 补三块测试：analyses 详情、ai-status 探测、静态文件服务（含路径穿越拒绝） |

**前端（admin/）**

| 文件 | 改动 |
|---|---|
| `admin/src/api/analyses.ts` | 类型扩展（mode/report/thumb/highlights）+ `AnalysisReport` / `DimensionScore` 类型 |
| `admin/src/api/system.ts` | `AiStatus` 类型 + `getAiStatus()` + `testAiConnect()` |
| `admin/src/views/analyses/index.vue` | 列表加模式/封面列；详情改调详情接口 + 六维报告渲染（评分条/节奏/亮点/改进建议/封面与高光帧） |
| `admin/src/views/system/health.vue` | 新增「AI 网关」状态卡片 + 「测试 AI 连接」按钮 |

**文档**

| 文件 | 改动 |
|---|---|
| `docs/plans/75-B2-Admin同步AI网关功能.md` | 本方案 |
| `docs/README.md` / `docs/.vitepress/config.mts` | 同步条目 |

## 五、验收标准

- [ ] `GET /api/admin/analyses/{id}` 返回 `report`（六维 JSON 对象）/ `thumb` / `highlights`，历史脏数据不报错；
- [ ] Admin 分析页列表显示模式与封面缩略图；
- [ ] 详情弹窗完整展示六维评分条 / 节奏 / 亮点 / 改进建议 / 封面与高光帧；
- [ ] `GET /api/admin/system/ai-status` 返回三件套状态，Key 只返回掩码（无 Key 为空）；
- [ ] `/api/admin/system/files/../secret` 等穿越请求返回 404；
- [ ] 「测试 AI 连接」调用 `/ai-connect`，成功/失败均有 UI 反馈；
- [ ] 健康检查页「AI 网关」卡片正确显示各项状态与汇总；
- [ ] 图片路径兼容「相对路径」（走静态服务）与「绝对 URL」（原样）两种形态；
- [ ] `uv run pytest` 全绿、`pnpm build` 通过、`ruff check` 无错误。

## 六、实施步骤（TDD）

1. **后端测试先行（RED）**：`server/tests/` 补 `analyses` 详情返回完整报告、`ai-status` 探测、静态文件服务（含路径穿越拒绝）三块测试，确认失败；
2. **后端实现（GREEN/REFACTOR）**：Schema 扩展 → analyses 详情增强 → system.py 新增三端点 → `uv run pytest` / `ruff check` 全绿；
3. **Admin 前端**：analyses.ts / system.ts 类型与 API → analyses 列表与详情弹窗 → health 页 AI 网关卡片 → `pnpm build` 通过；
4. **文档同步**：本方案状态 📋 → 🚧 → 🏁，README / 侧边栏同步。

## 七、风险与注意事项

| 风险/注意 | 说明 |
|-----------|------|
| 历史脏数据 | `report` / `highlights` 可能是非法 JSON，后端解析容错返回 `None`，前端再兜底 |
| Key 安全 | `ai-status` 仅返回掩码（`sk-****abcd`）；`ai-connect` 由服务端代理调用，Key 不出服务端 |
| 路径穿越 | 静态文件服务必须 `normpath` 后限定在 `UPLOAD_DIR` 内，测试覆盖 `../` 场景 |
| 图片形态兼容 | 相对路径走静态服务，`http(s)://` 绝对 URL 原样直出 |
| ffmpeg 缺失 | 魔搭 CPU 实例可能缺系统 ffmpeg，健康检查需给出明确提示与 `imageio-ffmpeg` 兜底说明 |
