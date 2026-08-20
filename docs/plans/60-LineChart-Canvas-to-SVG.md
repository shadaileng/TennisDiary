> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 60 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 📋 待实施 |
> | 最后更新 | 2026-08-09 |
> | 对应功能/内容 | LineChart 组件从 Canvas 迁移到 SVG |
> | 关联文档 | `docs/reference/tennis-diary/src/components/Charts.tsx`（参考实现，未纳入版本管理） |

# Step 60：LineChart 组件从 Canvas 迁移到 SVG

## 一、问题背景

小程序统计页面的体重趋势折线图无法显示。经过多轮调试（移除 `getCurrentInstance`、双重 `nextTick`、`setTimeout`），问题依然存在。

### 根本原因

1. **Canvas 2D 在 uni-app 小程序自定义组件中存在节点获取问题**
   - `createSelectorQuery().select("#lineChart")` 在自定义组件中可能返回 null
   - `v-if` 切换导致 canvas 元素创建时序不确定
   - 小程序渲染层与逻辑层分离，异步获取节点不可靠

2. **参考实现使用 SVG**
   - Web 版 `Charts.tsx` 中的 `LineChart` 使用 SVG 绘制
   - SVG 是声明式渲染，无需异步节点获取
   - 代码简洁（56 行），逻辑清晰

## 二、目标

将 `LineChart` 组件从 Canvas 2D 迁移到 SVG，解决体重趋势图不显示的问题。

### 成功标准

- [ ] 体重趋势折线图正常显示
- [ ] 视觉效果与参考实现一致
- [ ] 代码简洁可维护
- [ ] 无控制台错误

## 三、方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. Canvas 2D | 高性能（大量数据点） | 异步节点获取复杂，小程序兼容性问题 |
| B. SVG | 声明式渲染，代码简洁 | 大数据量性能稍差（体重数据≤14 点无影响） |
| C. 第三方图表库 | 功能丰富 | 增加依赖，体积大 |

**选择方案 B（SVG）**，原因：
1. 体重数据最多 14 个数据点，SVG 性能完全够用
2. 与参考实现一致，便于维护
3. 代码简洁，无异步时序问题

## 四、实现步骤

### Step 1: 重写 LineChart 组件（SVG 版本）

**文件**: `miniapp/src/components/LineChart.vue`

**核心变更**:
- 移除 `<canvas>` 标签，改用 `<svg>`
- 使用 Vue 响应式自动重绘，无需 `nextTick`/`setTimeout`
- 保持相同的视觉效果（颜色、样式、标签）

**SVG 绘制逻辑**（参考 `Charts.tsx`）:
```vue
<svg viewBox="0 0 320 {height}" class="w-full">
  <!-- 面积填充 -->
  <path :d="areaPath" :fill="color" opacity="0.15" />
  <!-- 折线 -->
  <path :d="linePath" fill="none" :stroke="color" stroke-width="2.5" />
  <!-- 数据点 -->
  <circle v-for="(p, i) in points" :cx="p.x" :cy="p.y" r="3" fill="#fff" :stroke="color" />
  <!-- 标签 -->
  <text v-if="isEdge(i)" :x="p.x" :y="p.y - 8" text-anchor="middle">{{ value }}</text>
  <!-- X 轴标签 -->
  <text v-for="(d, i) in data" :x="points[i].x" :y="height - 2" text-anchor="middle">{{ d.label }}</text>
</svg>
```

### Step 2: 计算逻辑

**输入**: `data: { label: string; value: number }[]`, `height?: number`, `color?: string`, `unit?: string`

**处理**:
1. 固定宽度 320px（与参考实现一致）
2. 计算数据点的 x, y 坐标
3. 生成 SVG path 数据（折线 + 面积）
4. 标识首/尾/极值点用于显示数值标签

**输出**: SVG 元素

### Step 3: 样式保持

- 颜色：`#C8DA2B`（青柠色）
- 背景：透明
- 字体：10px/9px，颜色 `#171B14` / `#9CA3AF`
- 间距：padX=10, padY=18

### Step 4: 测试验证

1. 有数据时显示折线图
2. 无数据时显示"暂无数据"
3. 数据变化时自动重绘
4. 微信小程序开发者工具预览

## 五、代码结构

```
miniapp/src/components/
├── LineChart.vue    # 重写为 SVG 版本
└── ...
```

## 六、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| SVG 在小程序兼容性 | 低 | 中 | uni-app 小程序原生支持 SVG |
| 样式差异 | 低 | 低 | 参考 Web 版实现，保持一致 |
| 性能问题 | 极低 | 低 | 数据量小（≤14 点），无性能问题 |

## 七、验收标准

1. 体重趋势折线图正常显示
2. 数值标签显示正确（首/尾/极值点）
3. X 轴日期标签显示正确
4. 无控制台错误
5. 与参考实现视觉效果一致

## 八、参考实现

- Web 版: `docs/reference/tennis-diary/src/components/Charts.tsx`
- 当前版: `miniapp/src/components/LineChart.vue`
