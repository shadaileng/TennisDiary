# Changelog

本项目的所有显著变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.28.3] - 2026-08-07

### Fixed

- 修复后端微信登录报 `appid missing (41002)`：`server/app/core/config.py` 中 `load_dotenv` 的路径 `Path(__file__).resolve().parent.parent / ".env"` 少算一级 `.parent`（`config.py` 位于 `app/core/` 下，实际加载到不存在的 `server/app/.env`），导致 `WX_APPID`/`WX_SECRET` 始终为空、微信 `code2session` 收到空 `appid` 而返回 `41002`。修正为 `.parent.parent.parent` 指向 `server/.env`，登录鉴权恢复可用（见方案 37）

## [1.28.2] - 2026-08-07

### Fixed

- 修复日记/装备/统计 Tab 页面空白且无空态：业务页通过 `@/components` **桶导出**引入自定义组件时，uni-app mp-weixin 编译器无法将其注册进 `usingComponents`，编译产物各页面 `usingComponents` 为空，但 WXML 又引用了 `<empty>`/`<line-chart>`/`<popup>` 等未注册组件导致渲染为空白。将 `diary.vue`/`gear.vue`/`stats.vue`/`diary/form.vue`/`gear/form.vue` 五处组件引入改为**直接文件导入**（`@/components/xxx.vue`），重建后各页面 `usingComponents` 正确注册（见方案 36）

## [1.28.1] - 2026-08-07

### Fixed

- 修复 `src/utils/jwt.ts` 在微信小程序编译不兼容导致运行时 `module 'utils/jwt.js' is not defined`：重写 base64 解码实现，移除 `String.fromCharCode(...bytes)` 展开 `Uint8Array` 及 `atob` + `decodeURIComponent` 组合等高阶语法，改为循环逐字节解码 + 独立 UTF-8 解码函数，规避微信开发者工具 es6 二次编译解析失败而静默跳过注册该模块的问题

## [1.28.0] - 2026-08-07

### Added

- 引入游客模式（参考 tarot 项目）：登录态改为基于「token 有效（存在且未过期）」判断（新增 `src/utils/jwt.ts` 解析 JWT 的 `exp`），新增 `auth.isGuest` 游客态 getter；`App.vue` `onLaunch` 移除无条件静默登录，未登录即保持游客态、不再自动请求后台；日记/装备/统计页在游客态不发请求并展示 `Empty` 游客引导空态（「去登录」跳转「我的」页），`request.ts` 本地短路继续作为兜底（见方案 35）

## [1.27.0] - 2026-08-07

### Added

- 统计页「数据总览」增加空数据处理：新增 `statsLoading` 加载状态（避免加载中误显示空态）、`hasAnyData` 计算属性判断是否有统计数据，完全无数据时显示 `Empty` 空态引导并可跳转日记页记录（见方案 34）

## [1.26.0] - 2026-08-07

### Added

- 未登录友好提示：`request.ts` 网络层加未登录硬门控（`auth=true` 且无本地 token 时直接短路不发请求，3s 节流 toast 引导「请到『我的』页登录后使用」，401 统一引导）；三个数据 store（weight/diary/gear）`fetchList` 加 try/catch 吞错并 `console.error` 打印，`stats.vue` `getStats` 的 catch 补日志，消除未登录/请求失败时的未捕获 `MiniProgramError`（见方案 33）

## [1.25.0] - 2026-08-07

### Added

- Tailwind 小程序适配方案迁移：弃用 `tailwindcss-miniprogram-preset`，改用 `weapp-tailwindcss@^5`（Vite 插件，命名导出 `WeappTailwindcss`），配置 `rem2rpx` 单位转换 + 类名混淆，`tailwind.config.js` 去 preset 并加 `corePlugins.preflight: false`，PostCSS 插件配置抽到独立 `postcss.config.js`，`App.vue` 改用 `@tailwind utilities;`，根治 WXSS 对 `skewY`/`scaleY` 编译错误（见方案 32）

## [1.24.0] - 2026-08-06

### Added

- Phase 2 我的页：用户信息展示 + 手动登录/登出 + 设置入口（金额隐私开关、主题偏好），对接 `/api/auth/me`，见方案 31
- Phase 2 统计页：汇总卡片（累计打球/时长/平均强度/心情/总花费/装备数，对接 `/api/stats`）+ 体重管理（记录/历史/趋势折线图，对接 `/api/weights`），见方案 30
- 新增 `LineChart` canvas 折线图组件（`src/components/LineChart.vue`）
- Phase 2 装备页：画报卡片流 + 种类筛选 + 新增/编辑表单页 + 照片上传，对接 `/api/gears`，见方案 29
- `utils` 新增 `choosePhoto` 图片压缩工具（`uni.chooseMedia` + canvas 压缩），`services/data` 补充 `getGear` 详情接口
- Phase 2 日记页：日记列表页 + 新建/编辑表单页，对接 `/api/diaries`，见方案 28
- 新增 `Seg` / `EmojiScale` 表单组件
- 建立组件库地基：`Empty` / `NavBar` / `Cell` / `Field` / `Stepper` / `Tag` / `ActionSheet` / `Popup`（`src/components/`），见方案 27
- 迁移前端 `utils` 工具函数（枚举 / 日期 / 金额 / 聚合）
- 数据层 `services/data.ts` 封装全部接口 + 三个数据 store（diary/gear/weight）对接真实接口，见方案 27
- 静默登录门控：`auth` store 新增「曾登录」标志（storage 键 `td_has_logged_in`），`ensureLogin()` 仅在已持有 token 或曾登录过时才触发 `wx.login` → 后端登录链路，首次启动（从未登录）不再请求后台，等待用户手动登录；`logout()` 清除该标志，登出后不再自动登录（见方案 25）

## [1.23.1] - 2026-08-06

### Fixed

- 修复小程序 `app.wxss` 编译失败：`diary.vue` 的 Tailwind 冒号变体类 `active:opacity-90` 编译出 `.active\:opacity-90:active` 反斜杠转义选择器，WXSS 解析器不支持而报 `unexpected '\'` 错误；改为自定义类 `press-btn` + scoped `.press-btn:active`，并沉淀约束「小程序端禁用 Tailwind 冒号变体」
- 修复小程序静默登录 404：端口 8000 被另一项目（Tennis Motion System）占用，后端请求打到错误服务器；结束占用进程并启动 Tennis Diary 后端，`/api/auth/login` 恢复正常路由（见方案 24）

## [1.23.0] - 2026-08-06

### Added

- 前端构建期注入微信小程序配置（参照 shadaileng/tarot）：新增非 `VITE_` 前缀环境变量 `TD_APPID`（微信 AppID）与 `TD_URL_CHECK`（域名白名单校验开关），由 `vite.config.ts` 内联插件在 `closeBundle` 时写入构建产物 `dist/*/mp-weixin/project.config.json` 的 `appid` 与 `setting.urlCheck`，不改动 `src/manifest.json`、不进入打包产物；`miniapp/.gitignore` 补齐 `.env.*` 忽略（仅保留 `.env.example`），新增 devDependency `@types/node`

## [1.22.0] - 2026-08-05

### Added

- 前后端引入 `.env` 配置模板：前端 `config/index.ts` 改为读 `VITE_API_BASE_URL` / `VITE_REQUEST_TIMEOUT`（`import.meta.env`），未配置时按平台兜底；后台新增 `python-dotenv` 以绝对路径自动加载 `server/.env`；新增 `miniapp/.env.example` 与 `server/.env.example` 模板（仅模板提交，实际 `.env.*` 由各环境手动配置）
- 前端 storage 键名统一收口到 `src/constants/storage.ts`（`STORAGE_KEYS`），`request.ts` / `auth.ts` / `settings.ts` 均引用常量，消除 `td_*` 魔法字符串散落

## [1.21.0] - 2026-08-05

### Added

- 小程序端对接 B1 微信登录流程：`services/auth.ts` 封装 `getLoginCode()`（`uni.login` 取 code，小程序编译为 `wx.login`），`auth` store 的 `login()` 完成「取 code → 换 JWT → 取用户 → 持久化」链路，新增 `ensureLogin()` 静默登录（无 token 时 App.onLaunch 自动触发），登录失败提示并保持未登录态（Phase 1 小程序前端基础能力全部完成）

## [1.20.0] - 2026-08-05

### Added

- 小程序端封装网络层：`config/index.ts` 按平台区分 baseURL（小程序 `127.0.0.1` / H5 `localhost`），`services/request.ts` 封装 Promise 化 `get/post/put/delete` 并自动注入 JWT、统一 `ApiError` 与 401 处理，`services/auth.ts` 提供登录/获取用户 API，`auth` store 的 `login()` 对接网络层，`App.vue onLaunch` 恢复登录态与偏好

## [1.19.0] - 2026-08-05

### Added

- 小程序端搭建 Pinia 全局状态（`src/stores/`）：`auth`（token/用户登录态 + 持久化）、`diary`/`gear`/`weight`（数据列表，网络 action 待 Phase1-7 填充）、`settings`（金额隐私/主题偏好 + 持久化），并在 `main.ts` 注册 `createPinia()`

## [1.18.0] - 2026-08-05

### Added

- 小程序端完成 `types.ts` 类型定义迁移（`src/types/index.ts`）：字段命名对齐后台 B1 Pydantic Schemas（`created_at`/`buy_date`/`course_id` 等蛇形命名），区分主实体接口（含 `id`/`created_at`）与创建/更新入参（`*Create`/`*Update`），`RallyClip.video` 改用 `File`（小程序 `uni.chooseMedia`），补充后台交互类型 `User`/`Token`/`LoginRequest`/`Stats`/`MessageResponse`，保留 `Course`/`AISettings` 等前端本地类型

## [1.17.0] - 2026-08-05

### Changed

- 小程序 UI 组件方案变更：移除 `@vant/weapp`（原生组件无法被 Vite/Vue 编译，复制 `wxcomponents/` 与「构建 npm」两种引入方式均有硬伤），改用 Tailwind CSS 自定义组件；删除 `src/wxcomponents/`（约 500 个文件）、清理 `pages.json` usingComponents 与 `App.vue` 的 `--van-*` 变量，`diary.vue` 占位页改用 Tailwind 实现 Tab/Cell/按钮

## [1.16.0] - 2026-08-05

### Added

- 小程序建立标准目录结构（components/stores/types/utils/services/styles），配置四 Tab 底部 TabBar（日记/装备/统计/我的），生成橄榄绿/青柠主题占位图标并移除模板默认页

## [1.15.0] - 2026-08-05

### Added

- 初始化 uni-app（Vue3 + Vite + TS）小程序前端工程 `miniapp/`，接入 pnpm 工作区，`build:mp-weixin` / `dev:mp-weixin` / `type-check` 均通过

## [1.14.0] - 2026-08-05

### Added

- 实现文件下载接口（`GET /api/files/{filename}`）：按相对 `UPLOAD_DIR` 路径下载文件，含路径穿越防护、用户归属校验（仅可下载本人 Gear 引用的文件）、按扩展名推断 Content-Type

## [1.13.0] - 2026-08-05

### Added

- 实现统计汇总接口（`GET /api/stats`）：聚合当前用户的日记、装备、分析数据，返回训练次数/总时长/平均强度与心情/总花费/装备数/分析数与平均分

## [1.12.0] - 2026-08-05

### Added

- 实现打卡接口（`/api/checkin`）：训练营打卡查询 / 签到，同用户+同课程+同日期幂等，强制用户归属校验

## [1.11.0] - 2026-08-05

### Added

- 实现体重记录接口（`/api/weights`）：列表 / 添加 / 删除，强制用户归属校验

## [1.10.0] - 2026-08-05

### Added

- 实现装备 CRUD 接口（`/api/gears`）：列表 / 添加 / 详情 / 编辑 / 删除，强制用户归属校验

## [1.9.0] - 2026-08-05

### Added

- 实现日记 CRUD 接口（`/api/diaries`）：列表 / 创建 / 详情 / 编辑 / 删除，强制用户归属校验（B1 数据层首块）

## [1.8.0] - 2026-08-05

### Added

- 鉴权路由接入日志：登录成功 / 无效 code / code2session 异常均有日志输出

## [1.7.0] - 2026-08-05

### Added

- 后台新增基于 loguru 的统一日志系统（`app/core/logging.py`）：控制台 + 文件双输出，支持级别过滤、按大小滚动、按时间保留

## [1.6.0] - 2026-08-05

### Added

- 实现微信登录鉴权接口（`POST /api/auth/login`）：接收 `wx.login` code，换取 openid，自动创建用户并签发 JWT；新增 `GET /api/auth/me` 获取当前用户

## [1.5.0] - 2026-08-05

### Added

- 完善 Pydantic Schemas 并添加验证测试

## [1.4.0] - 2026-08-05

### Added

- 启动时自动创建运行时数据目录（`ensure_dirs`）

## [1.3.0] - 2026-08-05

### Added

- 统一 `data` 目录管理运行时数据（数据库 + 上传文件），新增 `.env.example` 配置模板

### Fixed

- 数据目录管理统一为 `data/`，避免数据库与上传文件分散

## [1.2.0] - 2026-08-05

### Added

- 引入 TDD 测试框架（pytest + httpx TestClient），补充 auth 与 models 单元测试

## [1.1.0] - 2026-08-05

### Added

- FastAPI 项目初始化：包含 ORM 模型（Diary / Gear / Weight / Analysis / Checkin / Post / User）、核心配置、uv 依赖管理

## [1.0.0] - 2026-08-05

### Added

- 初始化项目基础设施（gitignore / pnpm 工作区 / VitePress 文档站点配置）

---

**docs / test / chore 类型提交**（不触发版本变更，随所属功能版本记录）：

- `docs: 修复组件桶导出导致页面空白（方案 36 + 进度表/侧边栏/AGENTS/CHANGELOG 同步）`
- `docs: Phase 2-5 我的页完成 + Phase 2 业务页面收尾`
- `docs: Phase 2-4 统计页完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2-3 装备页完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2-2 日记页完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2-1 数据层与组件库完成（方案文档/进度表/侧边栏/AGENTS 同步）`
- `docs: Phase 2 业务页面实现总纲方案文档`
- `docs: 优化 README.md 与实际进度对齐（Phase B1 后台 + Phase1 前端全部完成）`
- `docs(plans): 新增 21 前后端 .env 配置模板方案`
- `chore(miniapp): 前端配置环境变量化与 storage 键名收口`
- `chore(server): 新增 python-dotenv 与 .env.example 模板`
- `docs(plans): 新增 Phase1-8 对接 B1 登录流程方案`
- `docs(plans): 新增 Phase1-7 网络层封装方案`
- `docs(plans): 新增 Phase1-6 Pinia store 搭建方案`
- `docs(plans): 新增 Phase1-5 types 类型迁移方案`
- `docs(plans): Phase1-4 变更为 Tailwind 自定义组件方案（替代 Vant）`
- `docs(plans): 新增 Phase1-1 ~ Phase1-3 子方案文档及侧边栏配置`
- `chore(miniapp): 集成 Tailwind CSS（橄榄绿/青柠主题色，vite 内联 postcss）`
- `feat(miniapp): 目录结构与四 Tab TabBar 占位页`
- `chore(miniapp): uni-app 工程初始化`
- `docs: 新增 B1-4 基于 loguru 的日志系统方案`
- `test(server): 补充日志系统单元测试`
- `docs(plans): 新增 Phase B1 后台执行方案文档及侧边栏配置`
- `docs: 添加 VitePress 文档站点与 Tennis Diary 迁移分析方案`
- `docs: 新增 README.md 和 AGENTS.md 项目文档`
