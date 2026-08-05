> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 16-Phase1-4 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | 组件方案决策：移除 Vant，采用 Tailwind CSS 自定义组件 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.1.0 | 变更方案：移除 `@vant/weapp`，改用 Tailwind CSS 自定义组件（原 v1.0.0 Vant 集成方案废弃） |
> | 2026-08-05 | v1.0.0 | 初版（Vant 4 Weapp 集成，后废弃） |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md)

# Step Phase1-4：组件方案决策 — Tailwind 自定义组件

## 一、目标

为小程序前端确定 UI 组件方案。经评估，**放弃 Vant 4（`@vant/weapp`），改用 Tailwind CSS 自定义组件**，替代原 Web 版 `UI.tsx` 自定义组件（TopBar/Section/Seg/Sheet/Toast/Confirm）。

## 二、背景与决策原因

### 2.1 为何放弃 Vant

`@vant/weapp` 是**原生微信小程序组件**（`.wxml` + `.wxss` + `.js`），不是 Vue 组件，无法被 Vite/Vue 编译器编译打包，只有两种引入方式，均存在明显问题：

| 引入方式 | 问题 |
|---|---|
| 复制 `wxcomponents/` | 全量复制约 **70 个组件 / 500 个文件**污染源码；按需复制需手动梳理依赖链，升级麻烦 |
| 微信开发者工具「构建 npm」 | 依赖图形界面交互操作，无法在**纯命令行 CI 工作流**（`pnpm build:mp-weixin`）中自动化 |

### 2.2 为何选择 Tailwind 自定义组件

- Tailwind CSS 已在 Phase1-3 完成集成，主题色（橄榄绿/青柠/米白）已就绪
- 小程序端用 Tailwind 工具类实现 UI，源码干净、零额外文件、跨端一致
- 需要复用的 UI 可抽成 `components/` 下的自定义组件，可控、易维护
- 更符合 uni-app 跨端理念，不绑定微信原生组件生态

## 三、技术方案

### 3.1 组件映射

原 Web 版 `UI.tsx` 组件由 Tailwind 实现或后续在 `src/components/` 抽组件：

| 原 `UI.tsx` | 实现方案 |
|---|---|
| `TopBar` | 原生导航栏（`pages.json` 配置） |
| `Section` | Tailwind 卡片布局（`bg-white rounded-card`） |
| `Seg` | Tailwind 自定义 Tab 切换（`border-b` + 激活态） |
| `Sheet` | `uni.showActionSheet` / `uni.showModal` 或自定义弹出层 |
| `Toast` | `uni.showToast` |
| `Confirm` | `uni.showModal` |

### 3.2 主题

沿用 Phase1-3 的 Tailwind 自定义色（`lime`/`olive`/`paper`/`ink`），无需额外的组件库主题变量。

## 四、执行步骤

1. 移除 `miniapp/package.json` 中的 `@vant/weapp` 依赖，执行 `pnpm install` 更新 lock 文件。
2. 删除 `src/wxcomponents/` 目录（约 500 个 Vant 原生组件文件）。
3. 清理 `src/pages.json` 中日记页的 `usingComponents`（`van-tab`/`van-tabs`/`van-cell`/`van-button`）。
4. 清理 `src/App.vue` 中的 Vant 主题 CSS 变量（`--van-*`）。
5. 用 Tailwind 类改写 `src/pages/diary/diary.vue` 占位页，实现 Tab 切换、Cell 列表、按钮等同效果。
6. 后续需复用的 UI（如按钮/单元格/Tab）在 `src/components/` 抽为自定义组件。

## 五、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/src/pages.json` | 移除 Vant usingComponents |
| `miniapp/src/App.vue` | 移除 Vant 主题变量 |
| `miniapp/src/pages/diary/diary.vue` | Tailwind 实现占位页 |
| `miniapp/package.json` | 移除 `@vant/weapp` |
| `miniapp/src/wxcomponents/` | 已删除 |

## 六、验收标准

- [x] `pnpm install` 无报错，`@vant/weapp` 已移除
- [x] `src/wxcomponents/` 已删除
- [x] 构建产物中无 `van-*` 残留
- [x] `diary.vue` 用 Tailwind 实现 Tab / Cell / 按钮
- [x] `pnpm build:mp-weixin` 编译通过
- [x] `type-check` 通过

## 七、提交拆分

1. `chore(miniapp): 移除 Vant，改用 Tailwind 自定义组件`
2. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-4 完成）`
