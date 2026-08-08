> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 12-Phase1 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-06 |
> | 对应功能/内容 | uni-app 小程序前端工程初始化与基础能力搭建 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md) · [B1-1：项目初始化](./02-B1-1-FastAPI项目初始化与目录结构.md) · [B1-5：微信登录鉴权（并入 B1-4 日志文档）](./05-B1-4-基于loguru的日志系统.md)

# Phase 1：uni-app 小程序前端工程初始化

> 本文档为 Phase 1 总纲，后续每个子步骤拆分为独立子方案文档（Phase1-1 ~ Phase1-8）。

## 一、目标

搭建 uni-app（Vue 3 + Vite + TypeScript）小程序前端工程骨架，完成工程配置、目录结构、底部 TabBar、Tailwind CSS 集成（自定义组件方案）、`types.ts` 类型迁移、Pinia store 搭建，并打通 B1 微信登录流程，为 Phase 2 数据层页面开发打好地基。

> 与主方案 5.3 一致，Phase 1 预计 **3-4 天**。

## 二、前置条件

- Phase B1 后台全部完成（✅），`/api/auth/login`、`/api/diaries` 等接口可用
- Node.js 18+、pnpm 已安装
- 微信开发者工具已安装（用于编译预览小程序）

## 三、技术栈与关键决策

| 项 | 决策 | 说明 |
|---|---|---|
| 框架 | uni-app（Vue 3 + Vite + TypeScript） | 编译目标：微信小程序；H5 端仅用于后端 API 联调测试 |
| 状态管理 | Pinia | 对应原 Web 版 React Context |
| UI 组件 | Tailwind CSS 自定义组件 | 放弃 Vant，用 Tailwind 实现原 `UI.tsx` 组件，需复用处抽 `components/` 组件 |
| 样式方案 | Tailwind CSS（`tailwindcss-miniprogram-preset`） | 沿用橄榄绿/青柠/米白主题色 |
| 路由 | uni-app `pages.json` | 替代 `react-router-dom` |
| 网络层 | `uni.request` 封装 + JWT | 对应原 Web 版 `fetch` |
| 登录 | `wx.login` → `/api/auth/login` → JWT | B1-5 已实现后端 |

### 3.1 主题色沿用（来自原 Web 版 `tailwind.config.js`）

| 色名 | 色值 | 用途 |
|---|---|---|
| `lime` | `#C8DA2B` | 主强调色（青柠） |
| `lime.soft` | `#F0F5CE` | 青柠浅底 |
| `lime.dark` | `#A8B822` | 青柠深色 |
| `olive` | `#242B1F` | 主深色（橄榄绿） |
| `olive.mid` | `#3A4433` | 橄榄绿中 |
| `olive.light` | `#6B7562` | 橄榄绿浅 |
| `paper` | `#F2F2EF` | 米白背景 |
| `ink` | `#171B14` | 文字墨色 |

圆角：`card: 20px`、`hero: 28px`；字体栈沿用原 `-apple-system / PingFang SC` 体系。

## 四、子步骤拆解

| Step | 内容 | 预计工时 | 状态 |
|------|------|:----:|:----:|
| Phase1-1 | uni-app 工程初始化（Vue3 + Vite + TS） | 0.5 天 | ✅ |
| Phase1-2 | 目录结构 + `pages.json` TabBar + 占位页 | 0.5 天 | ✅ |
| Phase1-3 | Tailwind CSS 集成（`tailwindcss-miniprogram-preset` + 主题色） | 0.5 天 | ✅ |
| Phase1-4 | 组件方案决策：Tailwind 自定义组件（替代 Vant） | 0.5 天 | ✅ |
| Phase1-5 | `types.ts` 类型定义迁移 | 0.5 天 | ✅ |
| Phase1-6 | Pinia store 搭建（auth / diary / gear 等） | 0.5 天 | ✅ |
| Phase1-7 | 网络层封装（`uni.request` + JWT 拦截） | 0.5 天 | ✅ |
| Phase1-8 | 对接 B1 登录流程（`wx.login` → JWT → 持久化） | 0.5 天 | ✅ |

---

## Step Phase1-1：uni-app 工程初始化

### 目标

创建 uni-app（Vue 3 + Vite + TypeScript）项目骨架，确保能在微信开发者工具中编译预览。

### 执行步骤

1. 使用官方 CLI 创建项目（`npx degit dcloudio/uni-preset-vue#vite-ts miniapp`）。
2. 安装依赖：`pnpm install`。
3. 配置 `src/manifest.json`（appid、微信小程序设置、`mp-weixin` 平台）。
4. 运行 `pnpm dev:mp-weixin` 并在微信开发者工具中预览。

### 产出物

- `miniapp/` 目录（uni-app 工程）
- `miniapp/src/manifest.json` 基础配置
- `miniapp/package.json` 依赖清单

### 验收标准

- [ ] `pnpm dev:mp-weixin` 编译通过
- [ ] 微信开发者工具可正常打开项目并预览默认首页
- [ ] 工程可 `pnpm build:mp-weixin` 产出构建包

---

## Step Phase1-2：目录结构与 TabBar

### 目标

建立标准目录结构，配置 `pages.json` 底部 TabBar，创建各 Tab 占位页面。

### 执行步骤

1. 建立目录结构（见下）。
2. 配置 `pages.json` 的 `pages` 与 `tabBar`（日记/装备/统计/我的 四个 Tab）。
3. 创建各占位页 `pages/diary/index.vue`、`pages/gear/index.vue`、`pages/stats/index.vue`、`pages/mine/index.vue`。
4. 配置 TabBar 图标与选中色（橄榄绿/青柠）。

### 目录结构

```
miniapp/src/
├── pages/                 # 页面
│   ├── diary/             # 日记（Tab）
│   ├── gear/              # 装备（Tab）
│   ├── stats/             # 统计（Tab）
│   ├── mine/              # 我的（Tab）
│   └── login/             # 登录页（可选）
├── components/            # 公共组件
├── stores/                # Pinia store
├── types/                 # 类型定义（types.ts 迁移）
├── utils/                 # 工具函数
├── services/              # API 封装（uni.request）
├── styles/                # 全局样式 / Tailwind
├── static/                # 静态资源（TabBar 图标等）
├── App.vue
├── main.ts
├── pages.json
├── manifest.json
└── uni.scss
```

### 验收标准

- [ ] 底部 TabBar 显示「日记/装备/统计/我的」四个 Tab
- [ ] 各 Tab 切换正常，占位页可展示
- [ ] TabBar 选中色为青柠主题色

---

## Step Phase1-3：Tailwind CSS 集成

### 目标

在 uni-app 中接入 Tailwind，沿用原 Web 版橄榄绿/青柠/米白主题色。

### 执行步骤

1. 安装 `tailwindcss` + `tailwindcss-miniprogram-preset` + `autoprefixer` + `postcss`。
2. 迁移原 `tailwind.config.js` 的自定义颜色/圆角/字体到新配置（见 3.1 表）。
3. 配置 `postcss.config.js`（`tailwindcss: { config: 'tailwind.config.js' }` + `autoprefixer`）。
4. 在 `App.vue` 全局引入 Tailwind 指令（`@tailwind base/components/utilities`），并按 preset 说明处理小程序端 WXSS 兼容。

### 关键注意

- 小程序端无 `hover:`/媒体查询等部分能力，需遵循 `tailwindcss-miniprogram-preset` 约定。
- H5 端可直接使用完整 Tailwind，便于后端联调。

### 产出物

- `miniapp/tailwind.config.js`（含主题色）
- `miniapp/postcss.config.js`
- `miniapp/src/styles/` 全局样式入口

### 验收标准

- [ ] `class="text-olive bg-lime"` 等自定义色 class 生效
- [ ] `rounded-card` 等自定义圆角生效
- [ ] 小程序端与 H5 端编译均通过

---

## Step Phase1-4：组件方案决策 — Tailwind 自定义组件

### 目标

确定 UI 组件方案：**放弃 Vant，改用 Tailwind CSS 自定义组件**，替代原 `UI.tsx` 组件。

### 决策原因

`@vant/weapp` 是原生小程序组件，无法被 Vite/Vue 编译；其两种引入方式均有硬伤：复制 `wxcomponents/`（约 500 个文件污染源码）、微信工具「构建 npm」（无法在纯命令行 CI 自动化）。Tailwind 已在 Phase1-3 集成，用其自定义组件更干净、可控、跨端一致。

### 执行步骤

1. 移除 `@vant/weapp` 依赖、删除 `src/wxcomponents/`、清理 `pages.json` 的 `usingComponents` 与 `App.vue` 的 `--van-*` 变量。
2. 用 Tailwind 类改写 `diary.vue` 占位页（Tab 切换 / Cell 列表 / 按钮）。
3. 需复用的 UI 后续在 `src/components/` 抽为自定义组件。

### 组件映射（原 `UI.tsx` → 实现方案）

| 原 `UI.tsx` | 实现方案 |
|---|---|
| `TopBar` | 原生导航栏（`pages.json` 配置） |
| `Section` | Tailwind 卡片布局（`bg-white rounded-card`） |
| `Seg` | Tailwind 自定义 Tab 切换 |
| `Sheet` | `uni.showActionSheet` / `uni.showModal` |
| `Toast` | `uni.showToast` |
| `Confirm` | `uni.showModal` |

### 验收标准

- [x] `pnpm install` 无报错，`@vant/weapp` 已移除
- [x] `src/wxcomponents/` 已删除，构建产物无 `van-*` 残留
- [x] `diary.vue` 用 Tailwind 实现 Tab / Cell / 按钮
- [x] `pnpm build:mp-weixin` 与 `type-check` 通过

---

## Step Phase1-5：`types.ts` 类型迁移

### 目标

将原 Web 版 `types.ts` 的类型定义迁移到小程序端，作为前端数据模型基准。

### 执行步骤

1. 将 `docs/reference/tennis-diary/src/types.ts` 迁移为 `miniapp/src/types/index.ts`。
2. 字段命名对齐后台 B1 Pydantic Schemas（`createdAt`→`created_at`、`buyDate`→`buy_date`、`courseId`→`course_id` 等蛇形命名）。
3. 区分主实体接口（`*Response`，含 `id`/`created_at`）与创建/更新入参（`*Create`/`*Update`）。
4. `RallyClip.video` 由 `Blob` 改为 `File`（小程序 `uni.chooseMedia`）；`Course`/`AISettings`/`RallyClip` 保留为前端本地类型。
5. 补充后台交互类型：`User`、`Token`、`LoginRequest`、`Stats`、`MessageResponse`。

### 产出物

- `miniapp/src/types/index.ts`（迁移完成）

### 验收标准

- [x] 主实体字段语义与原 `types.ts` 一致（命名对齐 B1 后台）
- [x] 含创建/更新入参类型，供网络层与页面使用
- [x] `Course`/`AISettings`/`RallyClip` 等前端本地类型保留
- [x] TypeScript 编译无类型错误

---

## Step Phase1-6：Pinia store 搭建

### 目标

创建全局状态 store，对应原 Web 版 React Context。

### 执行步骤

1. 安装 `pinia`。
2. 创建 store：

   | Store | 状态 | 职责 |
   |---|---|---|
   | `stores/auth.ts` | token / user | 登录态管理（对接 Phase1-8） |
   | `stores/diary.ts` | diaries | 日记列表/当前项（Phase 2 填充） |
   | `stores/gear.ts` | gears | 装备列表（Phase 2 填充） |
   | `stores/weight.ts` | weights | 体重记录（Phase 2 填充） |
   | `stores/settings.ts` | 主题/隐私开关 | 金额隐私、视觉偏好 |

3. 在 `main.ts` 注册 Pinia（`app.use(createPinia())`）。
4. 网络相关 action（`fetchList` 等）暂为空实现，待 Phase1-7 网络层接入填充。

### 产出物

- `miniapp/src/stores/*.ts`（auth / diary / gear / weight / settings + index.ts）

### 验收标准

- [x] `pinia` 依赖已安装
- [x] 各 store 可被页面引用
- [x] `auth` store 具备 token 读写与持久化能力
- [x] `settings` store 具备偏好持久化能力
- [x] `main.ts` 已注册 Pinia
- [x] 编译通过（type-check + build）

---

## Step Phase1-7：网络层封装

### 目标

封装 `uni.request`，统一 baseURL、JWT 注入、错误处理与登录失效跳转。

### 执行步骤

1. 创建 `config/index.ts`，用 `process.env.UNI_PLATFORM` 区分平台 baseURL（小程序 `127.0.0.1` / H5 `localhost`）。
2. 创建 `services/request.ts`，Promise 化 `get/post/put/delete`，自动注入 `Authorization`，统一 `ApiError` 与 401 处理。
3. 创建 `services/auth.ts`（`login`/`getMe`）。
4. `stores/auth.ts` 的 `login(code)` 对接网络层；`App.vue onLaunch` 调用 `init()` 恢复登录态与偏好。

### 产出物

- `miniapp/src/config/index.ts`
- `miniapp/src/services/request.ts`、`services/auth.ts`

### 验收标准

- [x] 请求自动携带 JWT
- [x] 401 统一处理（清登录态 + 提示）
- [x] H5 与小程序双端 baseURL 正确（编译产物验证）
- [x] type-check 与 build 通过

---

## Step Phase1-8：对接 B1 登录流程

### 目标

实现 `wx.login()` → `/api/auth/login` → 存储 JWT 的完整链路，支持首次启动静默登录。

### 执行步骤

1. `services/auth.ts` 封装 `getLoginCode()`（小程序 `uni.login` / H5 mock）。
2. `stores/auth.ts` 的 `login()` 完成「取 code → 换 JWT → 取用户 → 持久化」链路；新增 `ensureLogin()` 静默登录。
3. `App.vue onLaunch` 先 `init()` 恢复登录态，再 `ensureLogin()` 无 token 时自动登录。
4. 登录失败 `showToast` 提示并保持未登录态。

### 验收标准

- [x] 首次启动自动完成登录并取得 JWT
- [x] JWT 持久化，重启无需重复登录
- [x] `uni.login` 编译为 `wx.login`（产物验证）
- [x] 调用受保护接口（如 `/api/diaries`）自动携带 JWT

---

## 五、产出物汇总

| 操作 | 文件 | 说明 |
|---|---|---|
| 新增 | `miniapp/` 工程 | uni-app 前端工程 |
| 新增 | `miniapp/src/types/index.ts` | 类型定义迁移（对齐 B1 后台，含创建入参与后台交互类型） |
| 新增 | `miniapp/src/stores/*.ts` | Pinia store |
| 新增 | `miniapp/src/services/request.ts` | 网络层封装 |
| 新增 | `miniapp/src/services/auth.ts` | 登录 API |
| 新增 | `miniapp/tailwind.config.js` | Tailwind + 主题色 |
| 新增 | `miniapp/src/pages/*` | 页面与 TabBar |

## 六、验收标准（总纲）

- [ ] Phase1-1 ~ Phase1-8 各子步骤验收通过
- [ ] 工程可在微信开发者工具预览，四 Tab 正常
- [ ] Tailwind 主题色 + 自定义组件生效
- [ ] 登录流程打通，能调用 `/api/diaries` 等受保护接口
- [ ] H5 端可用于后端 API 联调测试
- [ ] 同步更新 CHANGELOG + AGENTS.md 状态表

## 七、提交拆分

1. `docs: 新增 Phase1 uni-app 前端工程初始化方案`
2. 每个子步骤按 TDD 完成各自提交：
   - `chore(miniapp): uni-app 工程初始化`
   - `feat(miniapp): 目录结构与 TabBar`
   - `chore(miniapp): 集成 Tailwind，自定义组件替代 Vant`
   - `feat(miniapp): types 迁移与 Pinia store`
   - `feat(miniapp): 网络层封装与登录流程`
3. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1 完成）`

## 八、风险与注意事项

| 项 | 说明 |
|---|---|
| Tailwind 小程序限制 | 无 `hover:`/部分伪类，遵循 preset 约定 |
| 组件复用 | 用 Tailwind 自定义组件，需复用处抽 `src/components/` 组件，避免重复代码 |
| 登录态管理 | `wx.login` code 5 分钟有效，需处理静默登录与 token 失效刷新 |
| 域名备案 | 开发期微信开发者工具勾选「不校验合法域名」，生产需备案域名 |
