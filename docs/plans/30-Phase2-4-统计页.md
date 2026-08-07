> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 30 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | Phase 2-4：统计页（汇总卡片 + 体重管理 + 折线图组件迁移），对接 `/api/stats` `/api/weights` |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施完成：LineChart canvas 组件 + 统计页 |
>
> **关联文档**：[Phase 2 总纲（26）](./26-Phase2-业务页面实现总纲.md) · [Phase 2-1 数据层（27）](./27-Phase2-1-数据层与组件库.md) · [B1-8 体重接口（08）](./08-B1-8-体重记录接口.md) · [B1-10 统计接口（10）](./10-B1-10-统计汇总接口.md)

# Step 30：Phase 2-4 统计页

## 一、目标

1. **统计页** `pages/stats/stats.vue`：改造占位页为「汇总卡片 + 体重管理」，对接 `/api/stats` `/api/weights`
2. **图表迁移**：新增 `LineChart.vue`（canvas 2D 折线图），把参考源码 SVG `LineChart` 改写为小程序 canvas 实现
3. **体重管理**：最新体重/累计变化/记录数 + 体重趋势折线图 + 历史记录列表 + 新增记录（体重 + 围度）

> **不做**：打卡热力图（MonthHeatmap/YearHeatmap）、技术评分雷达图（依赖 AI Analysis，Phase B2/Phase 4 实现）。

## 二、现状盘点

- ✅ 后端 `/api/stats` 返回 `StatsResponse`（total_sessions/total_duration/avg_intensity/avg_mood/total_cost/total_gears/total_analyses/avg_score）
- ✅ 后端 `/api/weights` CRUD（`WeightRecord` 含 weight/bust/waist/hip）
- ✅ `weight` store 已对接接口（`fetchList`/`create`/`remove`）
- ✅ `types` 有 `Stats`/`WeightRecord`/`WeightCreate`
- ✅ 组件库已有 Empty/Cell/CellGroup/Stepper
- ⚠️ `pages/stats/stats.vue` 是纯占位页
- ⚠️ 无图表组件（需新建 LineChart canvas 组件）

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| 图表实现 | 小程序不支持内联 SVG → 折线图用 **canvas 2D**，`uni.createSelectorQuery` 取节点尺寸 + dpr 适配 |
| 统计页结构 | 单页 `pages/stats/stats.vue`：汇总卡片区 + 体重管理区（记录/新增表单内联） |
| 汇总数据源 | `getStats()` 一次性拉取展示 |
| 体重数据源 | `weightStore.fetchList()`，`onShow` 刷新 |
| 体重新增 | 底部弹层 `Popup` + 表单（日期/体重/胸围/腰围/臀围），`weightStore.create` |
| 删除 | 历史记录行删除按钮，`uni.showModal` 确认 |
| 折线数据 | 取最近 14 条体重记录（升序），`LineChart` 展示 |
| 围度显示 | 历史记录行内联展示胸/腰/臀 |

## 四、技术方案

### 4.1 `LineChart.vue`（canvas 折线图）

输入 `data: {label, value}[]`，canvas 2D 绘制：
- 坐标计算逻辑复用参考源码 `Charts.tsx` LineChart（min/max/range、stepX、points）
- 绘制面积填充（透明度 0.15）+ 折线（strokeWidth 2.5）+ 数据点圆点 + 首尾/极值标签
- 横轴标签：数据 ≤8 全显示，>8 显示首尾
- canvas 尺寸：`uni.createSelectorQuery` 获取容器宽，高度固定（默认 110-130），dpr 缩放

```ts
props: { data: { label: string; value: number }[]; height?: number; color?: string; unit?: string }
```

### 4.2 统计页 `pages/stats/stats.vue`

**汇总卡片区**（来自 `/api/stats`）：
- 两列卡片：累计打球（total_sessions 次）、累计时长（total_duration）、平均强度（avg_intensity）、平均心情（avg_mood）
- 总花费（total_cost，按金额隐私隐藏）、装备数（total_gears）

**体重管理区**：
- 三格：当前体重（最新）/ 累计变化 / 记录数
- 体重趋势折线图（`LineChart`，数据 ≥2 条才显示）
- 历史记录列表（日期 + 体重 + 围度 + 删除）
- 「记录体重」按钮 → Popup 表单（日期/体重/胸围/腰围/臀围）

**onShow**：`weightStore.fetchList()` + `getStats()`

### 4.3 体重表单（Popup 内联）

- 日期 picker、体重 digit 输入（必填，20-300 校验）、胸/腰/臀 digit 选填
- 保存：`weightStore.create`，成功后刷新列表

## 五、产出物

### 新建文件

| 文件 | 说明 |
|---|---|
| `miniapp/src/components/LineChart.vue` | canvas 2D 折线图组件 |
| `docs/plans/30-Phase2-4-统计页.md` | 本方案文档 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `miniapp/src/components/index.ts` | 导出 LineChart |
| `miniapp/src/pages/stats/stats.vue` | 占位页 → 汇总 + 体重管理 |
| `docs/README.md` / `config.mts` / `AGENTS.md` | 文档同步 |

## 六、验收标准

- [x] 汇总卡片展示 `/api/stats` 数据（次数/时长/强度/心情/花费/装备数）
- [x] 体重三格（当前/变化/记录数）正确
- [x] 体重趋势折线图（canvas）绘制正确，数据 ≥2 条显示
- [x] 新增体重记录：`POST /api/weights` 成功并刷新列表
- [x] 删除体重记录：确认后 `DELETE`
- [x] 历史记录行显示体重 + 围度（胸/腰/臀）
- [x] 金额隐私开关隐藏总花费
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 构建成功

## 七、提交拆分

1. `feat(miniapp): 新增 LineChart canvas 折线图组件`（MINOR bump）
2. `feat(miniapp): 统计页（汇总卡片 + 体重管理 + 折线图）`（MINOR bump）
3. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase 2-4 完成）`

## 八、执行记录

- 2026-08-07：实施完成
  - 新增 `components/LineChart.vue`：canvas 2D 折线图（面积填充 + 折线 + 数据点 + 标签，dpr 适配，`createSelectorQuery().fields()` 取节点尺寸），坐标计算复用参考源码逻辑
  - `components/index.ts` 导出 LineChart
  - 重写 `pages/stats/stats.vue`：汇总卡片（`/api/stats` 六项）+ 体重管理（三格 + LineChart 趋势 + 历史记录 + Popup 新增表单），`onShow` 拉取
  - 验证：`pnpm type-check`、`pnpm build:mp-weixin` 通过；产物 `components/LineChart` 正常生成
