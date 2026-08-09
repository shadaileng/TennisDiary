> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 61 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-09 |
> | 对应功能/内容 | 修复 miniapp 构建期 Sass @import 弃用警告与循环 chunk 依赖警告 |
> | 关联文档 | [23-构建警告清理-Tailwind与Sass弃用警告](./23-构建警告清理-Tailwind与Sass弃用警告.md)、[59-小程序事件锚点与线上事件日志](./59-小程序事件锚点与线上事件日志.md) |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-09 | v1.0.0 | 初版 |

# Step 61：修复 miniapp 构建警告（Sass @import + 循环 chunk）

## 一、问题背景

`pnpm build:mp-weixin` 构建输出两条警告：

1. **Sass `@import` 弃用警告**（18 个文件）：
   ```
   DEPRECATION WARNING [import]: Sass @import rules are deprecated ...
   @import "@/styles/tokens.scss";
   ```
   Dart Sass 3.0.0 将移除 `@import`，推荐使用 `@use`。

2. **循环 chunk 依赖警告**：
   ```
   Circular chunk: stores/auth -> services/auth -> services/request -> utils/eventLogger -> stores/auth
   ```

## 二、根因分析

### 2.1 Sass @import 警告

18 个 `.vue` 文件的 `<style scoped lang="scss">` 中均单独写入了：
```scss
@import "@/styles/tokens.scss";
```
导致每个文件都触发一次弃用警告。

### 2.2 循环依赖

模块加载链：
```
stores/auth.ts
  └─ import { logInfo, logError } from "@/utils/eventLogger"
        └─ import { useAuthStore } from "@/stores/auth"   ← 循环！
```

`eventLogger.ts` 在模块顶层导入 `useAuthStore`，而 `stores/auth.ts` 也导入了 `eventLogger.ts`，形成循环。

## 三、修复方案

### 3.1 Sass @import → vite additionalData

**移除**所有 `.vue` 文件中的 `@import "@/styles/tokens.scss";` 行（共 18 个文件）。

在 `vite.config.ts` 的 `css.preprocessorOptions.scss.additionalData` 中统一注入：
```ts
css: {
  preprocessorOptions: {
    scss: {
      silenceDeprecations: ["legacy-js-api"],
      additionalData: `@use "@/styles/tokens.scss" as *;`,
    },
  },
},
```

`as *` 使变量以原始名称（如 `$color-lime`）直接可用，与原有 `@import` 行为一致，无需修改任何组件样式代码。

### 3.2 循环依赖修复

将 `eventLogger.ts` 中的顶层 `import { useAuthStore }` 移除，改为在 `flushOne()` 函数内延迟加载：
```ts
// 延迟导入，避免循环依赖
const { useAuthStore } = require("@/stores/auth");
const authStore = useAuthStore();
```

这样模块初始化时不再触发 `stores/auth` 的加载，循环被打破。

## 四、修改文件清单

| 文件 | 变更内容 |
|------|---------|
| `miniapp/vite.config.ts` | 添加 `additionalData: \`@use "@/styles/tokens.scss" as *;\`` |
| `miniapp/src/utils/eventLogger.ts` | 移除顶层 `import`，改用 `require` 延迟加载 `useAuthStore` |
| `miniapp/src/components/*.vue`（14个） | 删除 `@import "@/styles/tokens.scss";` 行 |
| `miniapp/src/pages/diary/diary.vue` | 同上 |
| `miniapp/src/pages/diary/form.vue` | 同上 |
| `miniapp/src/pages/gear/form.vue` | 同上 |
| `miniapp/src/pages/gear/gear.vue` | 同上 |
| `miniapp/src/pages/stats/stats.vue` | 同上 |

## 五、验证结果

```
> pnpm build:mp-weixin
...
DONE  Build complete.
```

构建日志中无 Sass 弃用警告、无循环 chunk 警告，构建正常通过。
