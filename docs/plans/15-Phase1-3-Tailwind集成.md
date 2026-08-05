> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 12-Phase1-3 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | Tailwind CSS 集成与橄榄绿/青柠主题色 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md)

# Step Phase1-3：Tailwind CSS 集成

## 一、目标

在 uni-app 小程序端接入 Tailwind CSS，沿用原 Web 版橄榄绿/青柠/米白主题色，实现 `text-olive`、`bg-lime`、`rounded-card` 等自定义工具类。

## 二、前置条件

- Phase1-1 / Phase1-2 完成（工程可编译、TabBar 生效）

## 三、技术方案

### 3.1 依赖与工具链

| 包 | 用途 |
|---|---|
| `tailwindcss` | 核心（使用 v3） |
| `tailwindcss-miniprogram-preset` | 小程序端预设，解决 rpx/px 转换与伪类限制 |
| `postcss` + `autoprefixer` | PostCSS 管线 |

### 3.2 关键注意

- 小程序端无 `hover:`、`focus:` 等部分伪类能力，遵循 preset 约定。
- `tailwindcss-miniprogram-preset` 会将 `px` 相关单位按微信 rpx 规则处理，需按 preset 说明配置。

## 四、详细执行步骤

### 4.1 安装依赖

```bash
cd /workspace/miniapp
pnpm add -D tailwindcss@^3 tailwindcss-miniprogram-preset postcss autoprefixer
```

### 4.2 创建 `tailwind.config.js`

迁移原 Web 版 `tailwind.config.js` 的 `theme.extend`（colors / borderRadius / fontFamily），并加载小程序 preset：

```js
// tailwind.config.js
const miniprogramPreset = require('tailwindcss-miniprogram-preset')
module.exports = {
  presets: [miniprogramPreset],
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        lime: { DEFAULT: '#C8DA2B', soft: '#F0F5CE', dark: '#A8B822' },
        olive: { DEFAULT: '#242B1F', mid: '#3A4433', light: '#6B7562' },
        paper: '#F2F2EF',
        ink: '#171B14',
      },
      borderRadius: { card: '20px', hero: '28px' },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'PingFang SC', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

### 4.3 在 `vite.config.ts` 显式配置 PostCSS

> **坑**：uni-app 的 vite 插件**不会**读取项目的 `postcss.config.js`，必须通过 Vite 的 `css.postcss` 内联注入，否则 `@tailwind utilities` 会原样输出。

```ts
// vite.config.ts
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

export default defineConfig({
  css: {
    postcss: {
      plugins: [tailwindcss("./tailwind.config.js"), autoprefixer()],
    },
  },
  plugins: [uni()],
});
```

> 使用内联 `css.postcss` 后，`postcss.config.js` 应删除，避免双配置源。

### 4.4 全局引入 Tailwind 指令

在 `App.vue` 的 `<style lang="scss">` 中加入 Tailwind 三层指令；按 preset 约定处理小程序 WXSS 兼容（通常需要额外处理，如针对小程序禁用 preflight / 使用 preset 的编码方案）。

### 4.5 验证

用自定义色 class（如 `text-olive` / `bg-lime` / `rounded-card`）在占位页中测试，确认编译后 class 生效。

## 五、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/tailwind.config.js` | 主题色 + 小程序 preset |
| `miniapp/vite.config.ts` | 显式注入 tailwindcss + autoprefixer PostCSS |
| `miniapp/src/App.vue` | 全局引入 Tailwind utilities |
| `miniapp/package.json` | 新增 tailwindcss / preset / postcss / autoprefixer / sass |

## 六、验收标准

- [x] `pnpm install` 无报错
- [x] 自定义色 class（`text-olive` / `bg-lime` / `rounded-card`）在占位页生效
- [x] 小程序端与 H5 端编译均通过
- [x] `type-check` 通过

## 七、提交拆分

1. `docs: 新增 Phase1-3 Tailwind 集成方案`
2. `chore(miniapp): 集成 Tailwind CSS 与橄榄绿主题`
3. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-3 完成）`
