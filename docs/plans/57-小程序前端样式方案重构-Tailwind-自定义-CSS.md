> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 57 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 小程序前端样式方案重构：Tailwind 工具类 → 自定义 CSS 类 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
| 2026-08-08 | v1.1.0 | 实施完成 |
| 2026-08-08 | v1.1.0 | 实施完成 |
>
> **关联文档**：[Step 56 视觉样式改造](./56-小程序前端视觉样式与交互适配改造.md) · tarot 参考项目 `docs/reference/tarot/`（未纳入版本管理）

# Step 57：小程序前端样式方案重构 — Tailwind → 自定义 CSS

## 一、目标

解决 `weapp-tailwindcss` 插件内容扫描失效问题，将日记/装备/统计三页的 Tailwind 工具类改为自定义 CSS 类，参考 tarot 项目实现方式。

## 二、问题根因

### 2.1 当前问题

- `weapp-tailwindcss` 插件的内容扫描未正确识别 Vue 文件中的 Tailwind 类名
- `app.wxss` 仅生成 301 行基础样式，缺少 `gap`、`padding`、`margin`、`shadow` 等常用工具类
- 页面 `<wxml>` 中仍保留原始类名（如 `gap-2`、`p-4`），但对应的 CSS 未生成

### 2.2 tarot 参考方案

- tarot 项目**不使用 Tailwind 工具类**
- 样式写在 `<style lang="scss" scoped>` 中，使用自定义类名（如 `.draw-page`、`.section-title`）
- `weapp-tailwindcss` 仅处理 `app.css` 中的 `@tailwind utilities`，生成基础样式
- 页面特有样式通过自定义 CSS 类实现

## 三、技术方案

### 3.1 样式策略

| 原方案 | 新方案 |
|--------|--------|
| Tailwind 工具类（`gap-2`、`p-4`） | 自定义 CSS 类（`.gap-sm`、`.p-page`） |
| `weapp-tailwindcss` 生成 CSS | `<style scoped>` 定义 CSS |
| 类名混淆（`text-_b10px_B`） | 语义化类名（`.text-sm`） |

### 3.2 设计 Token

在 `src/styles/tokens.scss` 中定义设计 Token：

```scss
// 颜色
$color-lime: #C8DA2B;
$color-lime-dark: #A8B822;
$color-lime-soft: #F0F5CE;
$color-olive: #242B1F;
$color-olive-light: #6B7562;
$color-paper: #F2F2EF;
$color-ink: #171B14;
$color-white: #FFFFFF;

// 圆角
$radius-card: 20px;
$radius-hero: 28px;
$radius-full: 9999px;

// 阴影
$shadow-card: 0 1px 8px rgba(23, 27, 20, 0.04);
$shadow-card-md: 0 1px 8px rgba(23, 27, 20, 0.06);
$shadow-fab: 0 6px 20px rgba(200, 218, 43, 0.5);

// 间距
$space-xs: 4px;
$space-sm: 8px;
$space-md: 16px;
$space-lg: 24px;
$space-xl: 32px;
```

### 3.3 页面改造

#### 日记页 `pages/diary/diary.vue`

**改造前**：
```html
<view class="page bg-paper min-h-screen flex flex-col">
  <view class="m-4 mb-2 rounded-hero bg-olive p-5 overflow-hidden">
    <text class="text-lime text-[10px] font-bold tracking-[0.25em]">ONE SWING AT A TIME</text>
  </view>
</view>
```

**改造后**：
```html
<view class="diary-page">
  <view class="diary-hero">
    <text class="diary-hero-slogan">ONE SWING AT A TIME</text>
  </view>
</view>
```

```scss
<style scoped>
.diary-page {
  background-color: $color-paper;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.diary-hero {
  margin: $space-lg $space-lg $space-sm;
  border-radius: $radius-hero;
  background-color: $color-olive;
  padding: $space-xl;
  overflow: hidden;
  position: relative;
}

.diary-hero-slogan {
  color: $color-lime;
  font-size: 10px;
  font-weight: bold;
  letter-spacing: 0.25em;
}
</style>
```

#### 装备页 `pages/gear/gear.vue`

类似改造，定义 `.gear-page`、`.gear-hero`、`.gear-card` 等类。

#### 统计页 `stats/stats.vue`

类似改造，定义 `.stats-page`、`.stats-card`、`.stats-grid` 等类。

## 四、执行拆分

| Step | 内容 | 产出 |
|------|------|------|
| **57.1** | 创建 `src/styles/tokens.scss` | 设计 Token 文件 |
| **57.2** | 改造日记页 | `pages/diary/diary.vue` |
| **57.3** | 改造装备页 | `pages/gear/gear.vue` |
| **57.4** | 改造统计页 | `pages/stats/stats.vue` |
| **57.5** | 测试与验证 | `pnpm build:mp-weixin` + 真机测试 |

## 五、验收标准

- [ ] `src/styles/tokens.scss` 定义完整设计 Token
- [ ] 三个页面无 Tailwind 工具类，全部使用自定义 CSS 类
- [ ] `pnpm type-check` 通过
- [ ] `pnpm build:mp-weixin` 构建成功
- [ ] 微信开发者工具中视觉还原参考源码

## 六、风险与注意事项

1. **rpx 单位**：小程序建议使用 `rpx` 而非 `px`，设计 Token 中统一使用 `rpx`
2. **scoped 样式**：确保所有样式都在 `<style scoped>` 中定义
3. **组件复用**：公共样式（如 `.card`、`.btn`）可提取到 `src/styles/common.scss`

## 七、提交拆分

1. `feat(miniapp): 新增设计 Token 文件 src/styles/tokens.scss`
2. `feat(miniapp): 日记页样式重构（Tailwind → 自定义 CSS）`
3. `feat(miniapp): 装备页样式重构（Tailwind → 自定义 CSS）`
4. `feat(miniapp): 统计页样式重构（Tailwind → 自定义 CSS）`

## 八、执行记录

- 2026-08-08：实施完成
  - 新增 src/styles/tokens.scss：设计 Token（颜色/圆角/阴影/间距/字体）
  - 改造 pages/diary/diary.vue：Tailwind 工具类 → 自定义 CSS 类（.diary-page/.diary-hero/.diary-card 等）
  - 改造 pages/gear/gear.vue：Tailwind 工具类 → 自定义 CSS 类（.gear-page/.gear-hero/.gear-card 等）
  - 改造 pages/stats/stats.vue：Tailwind 工具类 → 自定义 CSS 类（.stats-page/.stats-card/.stats-weight 等）
  - 验证：pnpm type-check、pnpm build:mp-weixin 通过；各页面 wxss 正确生成
