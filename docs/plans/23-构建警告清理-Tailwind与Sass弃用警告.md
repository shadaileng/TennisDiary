> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 23 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-06 |
> | 对应功能/内容 | 清理小程序构建期 4 条弃用警告（Tailwind purge/darkMode + Sass @import/legacy-js-api） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-06 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1-3：Tailwind CSS 集成](./15-Phase1-3-Tailwind集成.md) · [Step 22：前端环境变量](./22-前端环境变量-AppID与域名白名单校验.md)

# Step 23：构建警告清理 — Tailwind 与 Sass 弃用警告

## 一、目标

消除 `pnpm build:mp-weixin` 构建日志中的 4 条弃用警告，构建产物与样式输出保持一致：

| # | 警告 | 来源 |
|---|------|------|
| 1 | Tailwind `purge`/`content` 配置已变更 | `tailwindcss-miniprogram-preset` 的 `defaultPreset` 内置旧版 `purge` 键 |
| 2 | Tailwind `darkMode: false` 等同于 `media` | 同一 preset 内置 `darkMode: false` |
| 3 | Sass `@import` 规则已弃用 | `src/App.vue` 使用 `@import "tailwindcss/utilities"` |
| 4 | Sass legacy JS API 已弃用 | Vite 5.2 + uni-cli-shared 内部使用旧版 `sass.render` |

## 二、决策记录

| 决策点 | 结论 |
|---|---|
| `purge`/`darkMode` 处理 | 在 `tailwind.config.js` 顶层用 `purge: undefined` / `darkMode: 'media'` 覆盖 preset 旧值。Tailwind 配置合并为 `defaults` 语义（先到先得），用户配置先于 preset 生效，`purge: undefined` 作为自有属性可让 merged 配置中 `purge` 为 falsy，从而跳过 `normalizeConfig` 的校验警告 |
| `@import` 处理 | 改为 `@use "tailwindcss/utilities"`。`tailwindcss/utilities` 解析到 `utilities.css`（内容即 `@tailwind utilities;`），`@use` 加载纯 CSS 模块会原样输出该指令，postcss/tailwind 照常处理（已用 sass compileString 验证） |
| `legacy-js-api` 处理 | 仅**静默**（`silenceDeprecations`），不做代码升级。根治需升级 vite/uni 使用 modern API，改动大且有兼容风险；uni-cli-shared 的 scss 管线会把 `css.preprocessorOptions.scss` 透传给 `sass.render`，sass ≥1.79 的 legacy API 支持 `silenceDeprecations` |

## 三、技术方案

### 3.1 `miniapp/tailwind.config.js`

在 `presets` 之后、`content` 之前新增两个顶层键：

```js
module.exports = {
  presets: [defaultPreset],
  purge: undefined,      // 覆盖 preset 中的旧版 purge，消除 Tailwind v3 警告
  darkMode: 'media',     // 覆盖 preset 中的 false，消除 darkMode 警告
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  // ...其余不变
}
```

### 3.2 `miniapp/src/App.vue`

```scss
// 原：@import "tailwindcss/utilities";
@use "tailwindcss/utilities";
```

### 3.3 `miniapp/vite.config.ts`

`css` 中新增 `preprocessorOptions.scss.silenceDeprecations`：

```ts
css: {
  preprocessorOptions: {
    scss: {
      silenceDeprecations: ['legacy-js-api'],
    },
  },
  postcss: {
    plugins: [tailwindcss('./tailwind.config.js'), autoprefixer()],
  },
},
```

> `import` 已通过 `@use` 根治，故只静默 `legacy-js-api`，避免掩盖真实的 `@import` 回归。

## 四、产出物

| 文件 | 改动 |
|---|---|
| `docs/plans/23-构建警告清理-Tailwind与Sass弃用警告.md` | 本方案文档 |
| `miniapp/tailwind.config.js` | 新增 `purge: undefined`、`darkMode: 'media'` |
| `miniapp/src/App.vue` | `@import` → `@use` |
| `miniapp/vite.config.ts` | 新增 `css.preprocessorOptions.scss.silenceDeprecations` |
| `docs/README.md` | 文档一览 + 执行进度补 23 |
| `docs/.vitepress/config.mts` | plans 侧边栏补 23（并补漏的 22） |

## 五、验收标准

- [ ] `pnpm build:mp-weixin` 构建日志不再出现上述 4 条警告，仍 `DONE Build complete.`
- [ ] 产物 `dist/build/mp-weixin/app.wxss` 仍包含 Tailwind 工具类（如 `lime` / `olive` 主题色）
- [ ] `pnpm type-check` 通过
- [ ] `pnpm docs:build` 通过（VitePress 侧边栏变更）

## 六、提交拆分

1. `chore(miniapp): 清理 Tailwind 与 Sass 构建弃用警告`

## 七、执行记录

- 2026-08-06：实施完成
  - `tailwind.config.js` 新增 `purge: undefined`、`darkMode: 'media'`
  - `App.vue` `@import` → `@use`
  - `vite.config.ts` 新增 `css.preprocessorOptions.scss.silenceDeprecations`
  - 验证：`pnpm build:mp-weixin` 4 条警告全部消失、`app.wxss` 工具类完整；`pnpm type-check`、`pnpm docs:build` 通过
