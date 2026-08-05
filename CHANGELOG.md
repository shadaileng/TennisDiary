# Changelog

本项目的所有显著变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
