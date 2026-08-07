> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 32 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | 将 Tailwind 小程序适配方案从 `tailwindcss-miniprogram-preset` 迁移到 `weapp-tailwindcss`，根治 WXSS 编译错误 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
>
> **关联文档**：[Step 23：构建警告清理](./23-构建警告清理-Tailwind与Sass弃用警告.md) · [Step 24：修复 WXSS 编译错误](./24-修复wxss编译错误与联调排障.md) · [Phase1-3：Tailwind CSS 集成](./15-Phase1-3-Tailwind集成.md)

# Step 32：Tailwind 适配方案迁移 — weapp-tailwindcss

## 一、背景

Step 24 曾用「方案 B（删除 `purge: undefined` 恢复内容扫描）」解决 `app.wxss` 中 `.transform` 类（含 `skewY()`/`scaleY()`）导致的 `unexpected '\'` 编译错误。

但 `tailwindcss-miniprogram-preset` 已属较旧的适配方案，且其 `defaultPreset` 内置 `purge`/`darkMode` 旧值、单位转换（px→rpx）与伪类处理机制与 Tailwind v3 及 uni-app 的贴合度有限。参考开源项目 [shadaileng/tarot](https://github.com/shadaileng/tarot)，改用 `weapp-tailwindcss`（Vite 插件）作为 Tailwind 小程序适配层，从根本上规避 WXSS 不支持 `skewY`/`scaleY` 等函数的问题，并获得类名混淆、`rem2rpx` 单位转换等能力。

## 二、决策记录

| 决策点 | 结论 |
|---|---|
| 适配方案 | 弃用 `tailwindcss-miniprogram-preset`，改用 `weapp-tailwindcss@^5`（Vite 插件入口 `weapp-tailwindcss/vite`） |
| 样式入口 | `@use "tailwindcss/utilities"` → `@tailwind utilities;`，插件通过 `cssEntries` 指定 `src/App.vue` 为处理入口 |
| 内容扫描 | `content: ['./index.html', './src/**/*.{vue,ts,tsx}']`，仅生成用到的类（坏类 `.transform` 不再出现） |
| 全局重置 | `corePlugins.preflight: false`，小程序无需 Tailwind preflight 重置 |
| 单位转换 | `rem2rpx: true`，Tailwind 的 `rem` 单位自动转 `rpx` |
| 类名混淆 | 插件自动对工具类类名做混淆（如 `.top-1` → `.top-1_f2`），并在 `.wxml` 同步改写，减小包体积 |

## 三、技术方案

### 3.1 依赖调整（`miniapp/package.json`）

- 移除：`tailwindcss-miniprogram-preset`
- 新增：`weapp-tailwindcss`（^5，当前锁定 5.2.11）

### 3.2 `miniapp/tailwind.config.js`

```js
module.exports = {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  darkMode: 'media',
  theme: { extend: { /* 主题色/圆角/字体不变 */ } },
  corePlugins: {
    preflight: false, // 小程序不需要 Tailwind 全局重置
  },
  plugins: [],
}
```

不再使用 `presets: [defaultPreset]` 与 `purge: undefined`。

### 3.3 `miniapp/postcss.config.js`（新增）

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

将原本写在 `vite.config.ts` `css.postcss.plugins` 里的 tailwind/autoprefixer 移到独立 PostCSS 配置文件，便于统一管理。

### 3.4 `miniapp/vite.config.ts`

```ts
import { WeappTailwindcss } from 'weapp-tailwindcss/vite'

plugins: [
  uni(),
  WeappTailwindcss({
    rem2rpx: true,
    cssEntries: [path.resolve(__dirname, 'src/App.vue')],
  }),
  injectWeixinConfigPlugin(),
],
```

> 注意：导出为**命名导出** `{ WeappTailwindcss }`，非默认导出；误用默认导入会导致 config 加载失败（`EIO`）。

### 3.5 `miniapp/src/App.vue`

```scss
@tailwind utilities;
```

## 四、产出物

| 文件 | 改动 |
|---|---|
| `docs/plans/32-Tailwind适配方案迁移-weapp-tailwindcss.md` | 本方案文档 |
| `miniapp/package.json` | 移除 `tailwindcss-miniprogram-preset`，新增 `weapp-tailwindcss@^5` |
| `miniapp/tailwind.config.js` | 去掉 `presets`/`purge: undefined`，新增 `corePlugins.preflight: false` |
| `miniapp/postcss.config.js` | **新增**，统一 PostCSS 插件配置 |
| `miniapp/vite.config.ts` | 移除内联 tailwind/autoprefixer，新增 `WeappTailwindcss` 插件 |
| `miniapp/src/App.vue` | `@use "tailwindcss/utilities"` → `@tailwind utilities;` |
| `pnpm-lock.yaml` | 依赖更新 |
| `AGENTS.md` | 样式方案描述更新 |

## 五、验收标准

- [ ] `pnpm build:mp-weixin` 构建成功，`DONE Build complete.`
- [ ] 产物 `dist/build/mp-weixin/app.wxss` 无 `skewY`/`scaleY` 坏类，无编译错误
- [ ] 产物中 Tailwind 工具类与 `.wxml` 类名改写一致（混淆类名双向同步）
- [ ] `pnpm build:h5` 构建成功（H5 不受 `rem2rpx` 影响）
- [ ] `pnpm type-check` 通过

## 六、提交拆分

1. `feat(miniapp): Tailwind 适配方案迁移至 weapp-tailwindcss`

## 七、执行记录

- 2026-08-07：实施完成
  - 依赖：移除 `tailwindcss-miniprogram-preset`，新增 `weapp-tailwindcss@^5`
  - 配置：`tailwind.config.js` 去 preset + `preflight: false`；新增 `postcss.config.js`；`vite.config.ts` 引入 `WeappTailwindcss({ rem2rpx, cssEntries })`（命名导出）；`App.vue` 改用 `@tailwind utilities;`
  - 验证：`pnpm build:mp-weixin`、`pnpm build:h5`、`pnpm type-check` 全部通过，`app.wxss` 无 `skewY`/`scaleY`
