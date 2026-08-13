> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 75-6 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-13 |
> | 对应功能/内容 | Phase 5 分享工坊（Canvas 卡片生成 + 保存图片 + 文案复制） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-13 | v1.0.0 | 初版（承接 [75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) §5 子方案 75-6） |
>
> **关联文档**：[75-B2 AI 网关三件套总纲](./75-B2-AI网关三件套总纲.md) · [75-5 Phase 4 电子教练](./75-5-Phase4-电子教练小程序页.md)

# 75-6：Phase 5 分享工坊

## 一、背景与目标

总纲 75-B2 的 Phase 5 分享工坊：让用户把**网球数据成果**（本月战报 / 今日日记 / AI 技术评分）一键生成可分享的**卡片图片** + 配套**文案**，用于发朋友圈 / 小红书等场景。本方案把参考版 `Share.tsx` 迁移为 uni-app 小程序页，纯前端实现，无后端改动。

| 能力 | 参考来源 | 职责 |
|------|---------|------|
| `pages/share/share` | `Share.tsx` | 模板选择 → 卡片 Canvas 绘制预览 → 保存图片 → 文案生成/复制 |

> **关键差异**：
> - 小程序无 DOM `<canvas>`，改用 `type="2d"` Canvas 节点 + `uni.canvasToTempFilePath` 导出图片，`uni.saveImageToPhotosAlbum` 保存（需授权）；
> - 参考版「发布管理」用本地 `db.posts`，本期**不做**（无后端 posts 接口，超纲），文案复制 + 保存图片即闭环；
> - AI 文案润色参考版走浏览器直连 AI，小程序端无对应接口，**本期不做**（文案为本地模板生成，可手动编辑后复制）。

## 二、现状

| 项 | 现状 |
|----|------|
| 页面 | 已有 coach 三页（75-5），**无 share 页**；pages.json 需注册 |
| 数据源 | `data.ts` 已有 `getDiaries()`（全量日记）、`getAnalyses()`（分析列表），Share 所需数据可本地聚合，无需新接口 |
| Canvas | 已有 `LineChart.vue` 用 `type="2d"` + `createSelectorQuery` 取 node 的先例，可参考其取节点写法 |
| 工具 | `utils/index.ts` 已有 `monthKey / todayStr / fmtDuration / fmtMoney / sumCosts / MOOD / INTENSITY`，与参考版 `Share.tsx` 所需一致 |
| 样式 | 自定义 CSS（Phase 2.6 起弃用 Tailwind），scoped SCSS 私有样式 |

## 三、数据源与聚合

| 模板 | 数据 | 聚合逻辑 |
|------|------|---------|
| 月度战报 | 本月日记 | `getDiaries()` 全量拉取 → `monthKey(d.date) === monthKey(today)` 过滤 → 次数 / 时长合计 / 花费合计 / 平均心情 |
| 今日日记 | 最新一篇 | `getDiaries()` 取 `date` 最新（倒序第一） |
| 技术评分 | 最新分析 | `getAnalyses()` 取 `items[0]`（接口已倒序） |

> 数据量级：日记/分析为个人数据（单用户），全量拉取可接受；无后端分页参数，暂不加。

## 四、卡片绘制（Canvas 2d）

### 4.1 画布与导出

- 画布尺寸 1080 × 1350（3:4 竖版，适合朋友圈/小红书）；
- `type="2d"` Canvas，`createSelectorQuery().in(instance.proxy).select("#shareCanvas").fields({node, size})` 取 node；
- `dpr = uni.getSystemInfoSync().pixelRatio || 2`，`canvas.width = 1080 * dpr`、`canvas.height = 1350 * dpr`，`ctx.scale(dpr, dpr)`；
- 导出：`uni.canvasToTempFilePath({ canvas: node })` → `uni.saveImageToPhotosAlbum({ filePath })`；保存前 `uni.authorize({scope: "scope.writePhotosAlbum"})`，拒绝时 `uni.openSetting` 引导。

### 4.2 绘制内容（对齐参考版 `Share.tsx` 三模板）

- **公共**：纸色背景、顶部橄榄绿头图（青柠网球装饰）、标题区、底部品牌标语 `用 Tennis Diary 记录我的网球成长 🎾`；
- **月度战报**：本月打球次数 / 挥拍时长（小时）/ 投入花费 / 平均心情 emoji，四白块统计卡；
- **今日日记**：类型 + 时长、日期时间、强度 emoji + label、心情 emoji + label、今日复盘（简易换行，超限截断）；
- **技术评分**：`kind` 标题 + AI 教练分析 · 日期、大评分球（lime 圆 + score）、六维横向进度条（对齐 `report-image.ts` 的 bar 逻辑）；
- 圆角矩形用 `rr()` 路径辅助（`arcTo` 四角），与参考版一致。

> **Canvas 字体**：小程序 Canvas 2d 字体用 `ctx.font = "700 34px sans-serif"`，无需引入 PingFang 名称，中英文均可渲染。

## 五、文案生成

| 模板 | 文案模板（本地生成，可编辑） |
|------|------|
| 月度战报 | `🎾 {m}月网球月报\n\n本月打球 {n} 次，挥拍 {h} 小时，投入 {cost}。\n每一次上场都是和自己的对话，慢慢来，比较快。\n\n#网球 #网球日记 #运动打卡` |
| 今日日记 | `🎾 今日份网球 {moodEmoji}\n\n{date} {type} {duration}\n{notes 或默认}\n\n#网球 #网球日记` |
| 技术评分 | `🤖 AI 教练给我的{kind}打了 {score} 分！\n\n{summary}\n最强项：{best}({bestScore}分) 💪\n下一步改进：{issue}\n\n#网球 #AI教练 #网球技术` |

- `textarea` 可编辑 → `uni.setClipboardData({ data: caption })` 复制；
- 生成时机：切换模板 / 重新进入时重新生成。

## 六、页面与交互

| 区块 | 内容 |
|------|------|
| 模板选择 | Seg 三选项（月度战报 / 今日日记 / 技术评分） |
| 卡片预览 | Canvas 绘制后 `canvasToTempFilePath` 显示为 `image`，可保存 |
| 保存图片 | 顶部「保存图片」按钮 → 授权 → saveImageToPhotosAlbum → toast |
| 文案区 | textarea 可编辑 + 「复制文案」按钮 + 「AI 润色」**不实现**（无后端接口） |
| 数据缺省 | 无日记/无分析时卡片画「还没有数据」占位 + 引导提示 |

## 七、验证

- `pnpm run type-check`（新增页面无错误，Field/LineChart 为既有问题）；
- `pnpm run build:mp-weixin` 通过；
- 后端无需改动，`uv run pytest` 回归（应仍 234 passed）。

## 八、实施步骤

1. 编写本方案文档（📋）；
2. 数据聚合：`share.vue` 内 `loadData()` 拉取日记/分析并按模板聚合；
3. Canvas 绘制：新增 `src/utils/shareCanvas.ts`（`drawShareCard(ctx, tpl, data)` 纯绘制函数，模板切换可复用）；
4. 页面：`pages/share/share.vue` 组装三区块，注册 pages.json，「我的」页加「分享工坊」入口；
5. 验证：`type-check` + `build:mp-weixin` + 后端回归；
6. 方案状态 🏁，同步 README / 侧边栏 / AGENTS.md。

## 九、风险与注意事项

| 风险 | 说明与对策 |
|------|-----------|
| 保存相册授权 | 首次触发 `uni.authorize(scope.writePhotosAlbum)`，拒绝时弹 `openSetting` 引导 |
| Canvas 导出黑图 | 绘制完成后需 `canvasToTempFilePath` 传 `canvas: node`（2d 必需），不能省 |
| 中文/emoji 渲染 | Canvas 2d 支持；emoji 用 `ctx.fillText` 正常；字体用系统 sans-serif |
| 数据量过大 | 全量拉取日记/分析仅限个人数据，量大时可后续加分页（本期不做） |
| 模板空数据 | 无日记/分析时绘制占位文案，避免空白卡片 |

## 十、完成情况

- **绘制工具**：新增 `miniapp/src/utils/shareCanvas.ts`，导出 `drawShareCard(ctx, tpl, data, MOOD, INTENSITY)`（1080×1350 逻辑尺寸，含 `rr` 圆角、`wrap` 折行、三模板绘制）与 `genCaption(tpl, data)`（本地文案模板，可编辑）。
- **页面**：新增 `pages/share/share.vue` — 模板 Seg 选择、`type="2d"` Canvas 绘制预览（`canvasToTempFilePath` 导出为 image）、保存到相册（`saveImageToPhotosAlbum` + 拒绝时 `openSetting` 引导）、文案 textarea 编辑 + 复制 + 重新生成；数据源 `getDiaries()` + `getAnalyses()` 本地聚合。
- **入口**：`pages.json` 注册 `pages/share/share`；mine.vue menu-section 新增「分享工坊」。
- **验证**：`pnpm run type-check`（新增页面无错误，Field/LineChart 为既有问题）、`pnpm run build:mp-weixin` 通过、后端全量 234 passed。