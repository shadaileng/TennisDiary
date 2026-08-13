> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 75-5 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-13 |
> | 对应功能/内容 | Phase 4 电子教练小程序页（选择视频 → 上传 → 等待 → 报告闭环 + 历史回看） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-13 | v1.0.0 | 初版（承接 [75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) §4.5 与 §5 子方案 75-5） |
>
> **关联文档**：[75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) · [75-4 分析报告落库](./75-4-分析报告落库与历史查询.md) · [75-3 MediaPipe 姿态推理](./75-3-MediaPipe姿态推理.md) · [75-2 视频上传与抽帧](./75-2-视频上传与抽帧.md) · [75-1 AI 评分代理接口](./75-1-AI评分代理接口.md)

# 75-5：Phase 4 电子教练小程序页

## 一、背景与目标

总纲 75-B2 目标：小程序端只需「上传视频 → 等待 → 出报告」。后端三件套（AI 评分 75-1 / 视频抽帧 75-2 / 姿态推理 75-3 / 报告落库 75-4）已完成，本方案实现 Phase 4 前端闭环，把参考版 `Coach.tsx` / `CoachAnalyze.tsx` / `CoachReport.tsx` 三页迁移为 uni-app 小程序页。

| 页面 | 参考来源 | 职责 |
|------|---------|------|
| `pages/coach/coach` | `Coach.tsx` | 电子教练入口：hero 区 + 历史分析列表 |
| `pages/coach/analyze` | `CoachAnalyze.tsx` | 三步交互：选择类型/上传视频 → 预览定位击球瞬间 → 等待分析 |
| `pages/coach/report` | `CoachReport.tsx` | 分析报告展示：封面 + 评分 + 六维点评 + 节奏/亮点/建议 + 删除 |

> **关键差异**：抽帧与姿态推理全部由服务端完成（75-2/75-3），小程序端不做任何本地图像处理；AI Key 不上传，未配置时后端自动返回本地降级报告（75-1 已内置）。

## 二、现状

| 项 | 现状 |
|----|------|
| 页面 | 已有 diary/gear/stats/mine/profile-edit，**无 coach 系列页**；pages.json 需注册 3 个新页 |
| 网络层 | `request.ts` 支持 `auth / handle401 / timeout`（AI 分析需 120s 超时），统一 `X-Auth-Token` |
| 上传 | 已有 `uploadAvatar`（uni.uploadFile）可参考；`BASE_URL + API_PREFIX` 拼接 |
| 视频组件 | 尚未使用 `<video>`；小程序端用 `uni.createVideoContext` 读取播放进度 |
| 数据层 | `data.ts` 无 analyses/video/ai 接口，需新增；`types/index.ts` 已有 `Analysis / AnalysisCreate / AnalysisReport / DimensionScore`（缺 `video_url`） |
| 入口 | 「我的」页 menu-section 可新增「电子教练」入口 |
| 样式 | 自定义 CSS（Phase 2.6 起弃用 Tailwind），scoped SCSS 私有样式 |

## 三、关键契约（前后端对齐）

### 3.1 上传（复用 75-2 `POST /api/video/upload`）

- multipart：`file` + `mode`(single/full) + `kind` + `hit_time`（可选，single 用）；
- 响应 data：
```json
{
  "frames": ["data:image/jpeg;base64,...", ...],  // 抽帧（AI 分析用）
  "frame_urls": ["videos/xxx_f0.jpg", ...],
  "duration": 8.0,
  "thumbnail": "data:image/jpeg;base64,...",      // 封面帧（报告展示用）
  "hit_time": 2.0,
  "mode": "single",
  "kind": "正手",
  "video_url": "videos/xxx.mp4"
}
```

### 3.2 AI 分析（复用 75-1 `POST /api/ai/analyze`）

- 入参：`{frames, kind, mode}`；出参：六维报告 `AnalysisReport`；
- 超时 120s（`request.ts` 传 `timeout: 120000`）；
- 未配置 Key / 失败时后端已降级返回 `score=0` 报告（HTTP 200）。

### 3.3 落库与历史（复用 75-4 `/api/analyses`）

- `POST /api/analyses`：入参 `AnalysisCreate`（含 `date/kind/mode/score/summary/ntrp/report/thumb/video_url`）；
- `GET /api/analyses`：历史列表（`data.items` + `data.total`）；
- `GET /api/analyses/{id}`：报告详情（`report` 为结构化 JSON）；
- `DELETE /api/analyses/{id}`：删除。

### 3.4 本地姿态测量（可选增强，复用 75-3 `POST /api/pose/analyze`）

- 入参：`{frames}`；出参：`{frames:[{landmarks}], metrics:{elbowAngle,kneeAngle,trunkLean}, detected}`；
- 用途：当 AI 报告为本地降级（`score=0`）时，用 `metrics` 展示「本地姿态测量」角值，补齐降级体验。

## 四、详细方案

### 4.1 数据层（`services/data.ts` + `types/index.ts`）

`data.ts` 新增：

| 函数 | 端点 | 说明 |
|------|------|------|
| `uploadVideo(filePath, formData)` | `POST /video/upload` | `uni.uploadFile` 直传，`X-Auth-Token` |
| `analyzeSwing(frames, kind, mode)` | `POST /ai/analyze` | `timeout: 120000` |
| `analyzePose(frames)` | `POST /pose/analyze` | `timeout: 60000` |
| `createAnalysis(body)` | `POST /analyses` | 落库 |
| `getAnalyses()` | `GET /analyses` | 历史列表 |
| `getAnalysis(id)` | `GET /analyses/{id}` | 详情 |
| `deleteAnalysis(id)` | `DELETE /analyses/{id}` | 删除 |

`types/index.ts`：`AnalysisCreate` 增加 `video_url?: string`；`Analysis` 增加 `video_url?: string`。

### 4.2 电子教练首页（`pages/coach/coach.vue`）

- hero 卡（深橄榄渐变 + 青柠光斑，参考 mine 页 profile-card）：标题「上传视频，让 AI 教练帮你复盘」+「开始分析」按钮 → `navigateTo /pages/coach/analyze`；
- 历史分析列表：`onShow` 拉 `getAnalyses()`，每条显示 kind 标签 + mode/date + summary + score（score=0 显示「本地」），点击 → `navigateTo /pages/coach/report?id=`；
- 空态：复用 `Empty.vue` 组件；
- 删除入口：报告页提供。

### 4.3 动作分析页（`pages/coach/analyze.vue`）

**Step 1 setup（选择类型 + 上传视频）**

- 模式切换 pill：单次挥拍 / 综合分析（参考 diary/form pill 样式）；
- kind Seg：`ANALYSIS_KINDS`（full 模式含「综合」，single 排除）；
- 「选择视频」按钮 → `uni.chooseVideo`（`maxDuration: 90`）→ 显示 `<video>` 预览。

**Step 2 video（single 定位击球瞬间）**

- `<video>` 组件 + `uni.createVideoContext`；
- 监听 `@pause` / `@timeupdate` 记录当前 `currentTime` 为 `hitTime`；
- 提供「设为击球瞬间」按钮：取 `videoCtx.getCurrentTime()`；
- 提示文案：single → 「拖动进度条，停在击球的瞬间」；full → 直接开始。

**Step 3 running（等待分析）**

1. `uploadVideo()` → 得 `frames / thumbnail / video_url`，进度「上传并抽取关键帧」；
2. `analyzeSwing(frames, kind, mode)` → 报告，进度「AI 教练正在分析（约 15-90 秒）」；
3. 若 `report.score === 0`（本地降级）→ 调 `analyzePose(frames)` 取 metrics 增强展示；
4. `createAnalysis({date, kind, mode, score, summary, ntrp, report, thumb, video_url})` 落库；
5. 成功后 `navigateTo /pages/coach/report?id=<id>`。

**防重复提交**：分析中禁用按钮 + `analyzing` 标志（参考 Phase 68 的 useActionLock 思路）。

### 4.4 分析报告页（`pages/coach/report.vue`）

- 按 `id` 从 URL query 读取 → `getAnalysis(id)`；
- 渲染：封面（`thumb`，dataURL 直显）+ 评分圆徽（score>0）+ kind/NTRP/mode/date + summary；
- 六维评分：`report.dimensions` → 分维度点评（ScoreBar 简版，横条 + 分数）；
- 节奏与战术 `rhythm`；亮点总结 `strengths`；待改进 & 建议 `improvements`；
- 本地降级（score=0 + metrics）：展示「本地姿态测量」角值卡（肘角/膝角/躯干倾角）；
- 顶部「删除」按钮 → `uni.showModal` 确认 → `deleteAnalysis(id)` → `safeNavigateBack`；
- 分享/长图（75-6）本期不做，留待 Phase 5。

### 4.5 入口与注册

- `pages.json` 注册 3 页（非 tabBar）：
  - `pages/coach/coach`「电子教练」
  - `pages/coach/analyze`「动作分析」
  - `pages/coach/report`「分析报告」
- 「我的」页 menu-section 增加「电子教练」入口 → `navigateTo /pages/coach/coach`。

## 五、文件改动清单

| 文件 | 改动 |
|------|------|
| `miniapp/src/pages/coach/coach.vue` | 新建：电子教练首页 |
| `miniapp/src/pages/coach/analyze.vue` | 新建：动作分析三步交互 |
| `miniapp/src/pages/coach/report.vue` | 新建：分析报告展示 |
| `miniapp/src/pages.json` | 注册 3 个页面 |
| `miniapp/src/pages/mine/mine.vue` | menu-section 增加「电子教练」入口 |
| `miniapp/src/services/data.ts` | 新增 video/ai/pose/analyses 接口 |
| `miniapp/src/services/upload.ts` | 新建：`uploadVideo`（uni.uploadFile 封装） |
| `miniapp/src/types/index.ts` | `AnalysisCreate`/`Analysis` 增加 `video_url` |
| `docs/README.md` / `docs/.vitepress/config.mts` / `AGENTS.md` | 同步进度 |

## 六、测试与验证计划

> 小程序端无单测框架，验证以**构建 + 类型检查 + 后端接口回归**为主（TDD 应用于后端已随 75-1~75-4 完成）。

1. **类型检查**：`cd miniapp && pnpm run type-check`（vue-tsc --noEmit）通过；
2. **构建**：`pnpm run build:mp-weixin` 成功，无构建警告；
3. **后端回归**：`cd server && uv run pytest` 全绿（新增前端调用不改变后端契约）；
4. **手动联调**（真机/开发者工具）：选择视频 → 上传 → 分析 → 报告展示 → 历史回看 → 删除，闭环可用。

## 七、验收标准

- [ ] 三页注册成功，`build:mp-weixin` 与 `type-check` 通过；
- [ ] 电子教练首页展示 hero + 历史列表 + 空态，入口可从「我的」进入；
- [ ] 分析页支持 chooseVideo 预览、single 模式定位击球瞬间、防重复提交；
- [ ] 上传 → AI 分析 → 落库 → 跳转报告闭环打通；
- [ ] 报告页展示封面/评分/六维点评/节奏/亮点/建议，本地降级显示姿态测量；
- [ ] 历史报告可回看、可删除；
- [ ] 后端 `uv run pytest` 全绿。

## 八、实施步骤

1. 编写本方案文档（📋）；
2. 数据层：`types` + `upload.ts` + `data.ts` 接口封装；
3. 页面：`coach.vue` → `analyze.vue` → `report.vue`，注册 pages.json，加「我的」入口；
4. 验证：`type-check` + `build:mp-weixin` + 后端回归；
5. 方案状态 🏁，同步 README / 侧边栏 / AGENTS.md。

## 九、风险与注意事项

| 风险 | 说明与对策 |
|------|-----------|
| AI 分析耗时（≤90s）| `request.ts` 传 `timeout:120000`；前端进度文案引导等待 |
| 视频上传体积/时长 | `uni.chooseVideo({maxDuration:90})`；后端 75-2 已有时长校验（single 15s/full 90s），超限提示 |
| 小程序 `<video>` 与后端时序 | 击球瞬间改从 `<video>` `timeupdate/pause` 事件 `e.detail.currentTime` 读取（`VideoContext` 无 `getCurrentTime`），格式为秒 |
| 本地降级体验 | score=0 时调 pose 接口展示角值，不让用户看到空报告 |
| 图片/视频展示 | `thumbnail` 为 dataURL 可直显；`video_url` 为相对路径，`resolveUploadUrl` 兜底（本期主要用 dataURL） |

## 十、完成情况

- **数据层**：`types/index.ts` 新增 `VideoUploadResult` / `PoseLandmark` / `PoseResult`，`Analysis`/`AnalysisCreate` 增加 `video_url`；`data.ts` 新增 `uploadVideo`（uni.uploadFile 直传 multipart，携带 `X-Auth-Token`）、`analyzeSwing`（timeout 120s）、`analyzePose`（timeout 60s）、`createAnalysis`/`getAnalyses`/`getAnalysis`/`deleteAnalysis`。
- **页面**：
  - `pages/coach/coach.vue`：hero 卡（青柠 CTA）+ 历史分析列表（封面/类型/评分），空态 Empty。
  - `pages/coach/analyze.vue`：三步流（①模式+类型 Seg ②选视频+击球瞬间定位 ③开始分析），`uploadVideo → analyzeSwing → (score=0 时 analyzePose 姿态增强) → createAnalysis`，防重复提交 + 进度文案。
  - `pages/coach/report.vue`：封面评分徽、摘要/NTRP、六维进度条、节奏战术、亮点、待改进建议、删除确认。
- **入口**：`pages.json` 注册 3 页；mine.vue menu-section 新增「电子教练」。
- **验证**：`pnpm run type-check`（新增页面无错误，Field/LineChart 为既有问题）、`pnpm run build:mp-weixin` 通过、后端全量 234 passed。