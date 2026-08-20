> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 58 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 踩坑记录：weapp-tailwindcss 内容扫描失效问题 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
| 2026-08-08 | v1.1.0 | 补充实施记录 |
>
> **关联文档**：[Step 56 视觉样式改造](./56-小程序前端视觉样式与交互适配改造.md) · [Step 57 样式方案重构](./57-小程序前端样式方案重构-Tailwind-自定义-CSS.md) · tarot 参考项目 `docs/reference/tarot/`（未纳入版本管理）

# Step 58：踩坑记录 — weapp-tailwindcss 内容扫描失效

## 一、问题现象

2026-08-08 改造日记/装备/统计前三 Tab 页时，发现界面样式完全失效，页面"太简陋"。

### 1.1 构建产物异常

```bash
# app.wxss 只有 301 行，缺少大量样式
$ wc -l dist/build/mp-weixin/app.wxss
301 dist/build/mp-weixin/app.wxss

# 关键样式缺失
$ grep "gap:" dist/build/mp-weixin/app.wxss
# 无输出

$ grep "padding:" dist/build/mp-weixin/app.wxss
# 只有 margin: 0; padding: 0; 重置样式

$ grep "margin:" dist/build/mp-weixin/app.wxss
# 只有 margin: 0; 重置样式

$ grep "shadow" dist/build/mp-weixin/app.wxss
# 无输出
```

### 1.2 WXML 与 WXSS 不对应

```html
<!-- diary.wxml 中有 gap-2 类 -->
<view class="flex items-center gap-2">

<!-- 但 diary.wxss 中没有 gap-2 的样式定义 -->
```

## 二、问题根因

### 2.1 weapp-tailwindcss 的工作原理

`weapp-tailwindcss` 插件通过**内容扫描**（content scanning）识别源文件中的 Tailwind 类名，然后生成对应的 CSS。

关键配置：
```typescript
// vite.config.ts
WeappTailwindcss({
  rem2rpx: true,
  cssEntries: [path.resolve(__dirname, 'src/app.css')],
})
```

### 2.2 扫描失败原因

经过对比 tarot 参考项目，发现关键差异：

| 项目 | 样式方案 | content 扫描 |
|------|---------|-------------|
| tarot | 自定义 CSS 类（`.draw-page`） | 不需要，类名已在 `<style scoped>` 中定义 |
| tennis-diary miniapp | Tailwind 工具类（`gap-2`, `p-4`） | 应该扫描，但**扫描失败** |

**根本原因**：`weapp-tailwindcss` 的内容扫描机制未能正确识别 Vue 文件中的 Tailwind 工具类。

可能的原因：
1. `tailwind.config.js` 的 `content` 配置路径问题
2. Vue 文件中的类名被 Vite 编译后发生变化
3. `weapp-tailwindcss` 版本与 uni-app 版本的兼容性问题

### 2.3 验证

```bash
# 直接测试 Tailwind 生成 CSS
$ node -e "
const tailwindcss = require('tailwindcss');
const postcss = require('postcss');
postcss([tailwindcss({ content: [{ raw: 'gap-3 p-4 m-2' }] })])
  .process('@tailwind utilities;', { from: 'test.css' })
  .then(r => console.log('has gap:', r.css.includes('gap:')));
"
# 输出: has gap: false（因为 content 配置不正确）
```

## 三、解决方案

### 3.1 短期方案：改用自定义 CSS（已实施）

参考 tarot 项目，放弃 Tailwind 工具类，改用自定义 CSS 类：

```scss
// 定义设计 Token
// src/styles/tokens.scss
$color-lime: #C8DA2B;
$space-md: 16px;
// ...

// 使用自定义类
// pages/diary/diary.vue
<style scoped lang="scss">
@import "@/styles/tokens.scss";

.diary-card {
  background-color: $color-white;
  padding: $space-md;
  gap: $space-md;
}
</style>
```

### 3.2 长期方案：修复 weapp-tailwindcss 配置

如需继续使用 Tailwind 工具类，需要：

1. **检查版本兼容性**：
   ```json
   // package.json
   "weapp-tailwindcss": "^5.0.6",  // tarot 使用版本
   // 当前 miniapp 使用
   "weapp-tailwindcss": "^5.2.11"
   ```

2. **调整 content 配置**：
   ```javascript
   // tailwind.config.js
   content: {
     files: ['./src/**/*.{vue,ts,tsx}'],
     transform: {
       vue: (content) => content.match(/[A-Za-z0-9-_]+/g) || [],
     },
   },
   ```

3. **或者升级到 Tailwind v4**：
   `weapp-tailwindcss@5.x` 支持 Tailwind v4，但需要调整配置。

### 3.3 推荐方案

**对于小程序项目，推荐使用自定义 CSS 方案**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| 自定义 CSS | 完全可控，无构建问题 | 需要手动定义类名 |
| Tailwind + weapp-tailwindcss | 开发效率高 | 内容扫描不稳定，调试困难 |

## 四、已改造文件

### 4.1 页面文件

| 文件 | 状态 |
|------|------|
| `pages/diary/diary.vue` | ✅ 已改造 |
| `pages/diary/form.vue` | ✅ 已改造 |
| `pages/gear/gear.vue` | ✅ 已改造 |
| `pages/gear/form.vue` | ✅ 已改造 |
| `pages/stats/stats.vue` | ✅ 已改造 |
| `pages/mine/mine.vue` | ✅ 已是自定义 CSS |
| `pages/profile-edit/profile-edit.vue` | ✅ 已是自定义 CSS |

### 4.2 组件文件

| 文件 | 状态 |
|------|------|
| `components/Seg.vue` | ✅ 已改造 |
| `components/EmojiScale.vue` | ✅ 已改造 |
| `components/MoneyToggle.vue` | ✅ 已改造 |
| `components/NavBar.vue` | ✅ 已改造 |
| `components/Popup.vue` | ✅ 已改造 |
| `components/ActionSheet.vue` | ✅ 已改造 |
| `components/Stepper.vue` | ✅ 已改造 |
| `components/Tag.vue` | ✅ 已改造 |
| `components/Cell.vue` | ✅ 已改造 |
| `components/CellGroup.vue` | ✅ 已改造 |
| `components/Empty.vue` | ✅ 已改造 |
| `components/Field.vue` | ✅ 已改造 |
| `components/LineChart.vue` | ✅ 已改造 |

## 五、经验总结

1. **小程序使用 Tailwind 需谨慎**：`weapp-tailwindcss` 的内容扫描机制不够稳定，大型项目容易出现样式丢失问题。

2. **参考成熟项目**：tarot 项目证明自定义 CSS 方案在小程序中完全可行，且维护成本更低。

3. **设计 Token 的重要性**：集中定义颜色、间距、圆角等 Token，可以保持项目视觉一致性，同时避免魔法数字。

4. **Sass @use vs @import**：
   - `@import` 已弃用，Dart Sass 3.0 将移除
   - 使用 `@use "@/styles/tokens.scss" as *` 替代

## 六、实施结果

已按照方案完成全部改造：
- 页面文件（7个）：diary/gear/stats/mine/profile-edit 及其 form 页
- 组件文件（13个）：Seg/EmojiScale/MoneyToggle/NavBar/Popup/ActionSheet/Stepper/Tag/Cell/CellGroup/Empty/Field/LineChart
- 设计 Token：src/styles/tokens.scss

所有页面已无 Tailwind 工具类残留，构建通过。

## 七、后续行动

- [ ] 评估是否值得投入时间修复 `weapp-tailwindcss` 配置
- [ ] 考虑是否将其他页面（如训练营、教练等）也改为自定义 CSS
- [ ] 更新 AGENTS.md 编码规范，明确样式方案选择
