# Changelog

本项目的所有显著变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.44.0] - 2026-08-11

### Added

- admin 新增全局 Loading 遮罩：axios 拦截器以请求计数器控制，所有 API 请求自动显示加载反馈；新增 `useActionLock` 组合式函数，列表页提交类操作（保存/重置密码/状态切换/删除）防重复提交并补充成功 toast 提示。详见 `docs/plans/68-Admin全局Loading与防重复提交.md`

## [1.43.4] - 2026-08-11

### Fixed

- 修复 admin 用户管理与事件日志详情中头像 URL 未拼接后台地址：`users/index.vue` 的 `getAvatarUrl` 与 `system/event-logs.vue` 的 `resolveAvatarUrl` 重新引入 `VITE_API_BASE_URL` 前缀，生产环境（管理端与后台不同域名）头像不再 404

## [1.43.3] - 2026-08-10

### Fixed

- 修复表单保存按钮可连点导致重复提交，新增 `saving` 锁防止并发请求

## [1.43.2] - 2026-08-10

### Fixed

- 修复 form 页面（日记/装备）在页面栈底时 `navigateBack` 抛错，改用 `safeNavigateBack` 自动回退到 tabBar

## [1.43.1] - 2026-08-10

### Fixed

- 修复 `eventLogger.ts` 中 `require("@/stores/auth")` 在小程序环境别名解析失败，导致模块未定义错误

## [1.43.0] - 2026-08-10

### Added

- 新增 Cloudflare Workers 反向代理（`proxy/` 目录），解决魔搭 `.ms.show` 网关 CORS 预检不返回 `X-Auth-Token` 导致 admin 前端跨域问题
- Worker 支持 OPTIONS 预检返回自定义 CORS 头 + 服务端转发透传 `X-Auth-Token`
- 新增方案文档 `docs/plans/67-Cloudflare-Workers-代理-ModelScope-方案.md`
- 新增 `proxy/README.md`，含快速开始、部署命令与前端接入说明
- `proxy/` 加入 pnpm workspace

## [1.42.3] - 2026-08-10

### Fixed

- 修复魔搭创空间鉴权头被网关占用导致登录后 `/me` 401：后端 `auth.py` 以 `APIKeyHeader` 统一读取自定义头 `X-Auth-Token`，移除 `Authorization` 回退与 `Request` 注入
- admin 前端 `api/index.ts` 请求头改用 `X-Auth-Token`
- miniapp 三处（`request.ts` / `auth.ts` / `eventLogger.ts`）请求头改用 `X-Auth-Token`
- 后端测试 `test_auth.py` / `admin/conftest.py` 同步改用 `X-Auth-Token`
- 诊断脚本 `diag-admin-auth.sh` 改用 `X-Auth-Token`，判断依据同步更新
- 新增方案文档 `docs/plans/66-ModelScope部署鉴权头兼容改造.md`

## [1.42.2] - 2026-08-10

### Fixed

- 修复魔搭创空间 `.ms.show` 公网访问被网关拦截返回 `10011402001`：部署脚本 `deploy-modelscope.sh` 新增 `MODEL_SCOPE_VISIBILITY` 变量（默认 `false`=公开体验），创建创空间时不再写死 `private: true`
- `.env.modelscope.example` 补充创空间可见性配置说明（`true`=私密 / `false`=公开体验）

## [1.42.1] - 2026-08-10

### Changed

- 魔搭构建加速：新增 `server/modelscope/Dockerfile` 专属镜像，apt 源替换为 `mirrors.aliyun.com`、pip/uv 索引指向阿里云 PyPI，解决跨境网络导致的构建慢问题
- `deploy-modelscope.sh` 优先复制魔搭专用 Dockerfile（含阿里云源加速），无则回退根目录通用版

### Fixed

- 修复魔搭创空间 Docker 构建失败：`server/.gitignore` 忽略 `uv.lock` 导致 GitHub Actions checkout 后缺文件，`Dockerfile` 的 `COPY pyproject.toml uv.lock ./` 在 COPY 阶段直接报错
- 将 `server/uv.lock` 纳入版本管理，保证本地 / CI / 魔搭三方依赖一致
- 部署脚本 `deploy-modelscope.sh` 在 `git add -A` 后补 `git add -f uv.lock pyproject.toml` 兜底，防止再次因忽略规则漏包

## [1.42.0] - 2026-08-09

### Added

- 新增 Server 部署方案（魔搭创空间 ModelScope Studio Docker 免费托管）：
  - 创建 `docs/plans/65-Server部署方案-ModelScope-创空间.md`（方案文档）
  - 创建 `server/modelscope/ms_deploy.json`（docker sdk / CPU 免费档 / 7860 端口）
  - 创建 `server/modelscope/README.md`（建仓、Secrets、反代、验证完整指南）
  - 创建 `server/scripts/deploy-modelscope.sh`（打包 + API Secrets + git push + 健康检查）
  - 创建 `server/.env.modelscope.example`（魔搭部署配置模板）
  - 创建 `.github/workflows/deploy-server-modelscope.yml`（push server/** 自动部署）
- 复用既有 Dockerfile（监听 7860），敏感环境变量通过魔搭 Secrets API 注入，不推送 git

## [1.41.1] - 2026-08-09

### Added

- 新增 Server 部署方案（Oracle Cloud Always Free 免费 VM）：
  - 创建 `docs/plans/64-Server部署方案-Oracle-Cloud.md`（方案文档）
  - 创建 `server/oci/README.md`（建机、安全组、Block Volume、初始化、部署完整指南）
  - 创建 `server/scripts/oci-bootstrap.sh`（VM 初始化：Docker/Compose/UFW/可选 Nginx+Let's Encrypt）
  - 创建 `server/scripts/deploy-oci.sh`（rsync 同步代码 + 远端 docker compose 重建 + 健康检查）
  - 创建 `server/.env.oci.example`（OCI SSH 配置模板）
  - 创建 `.github/workflows/deploy-server-oci.yml`（push server/** 自动部署到 OCI VM）
- 部署脚本支持 SSH 私钥「路径 / 内容」两种形式，CI 直接传私钥内容到临时文件
- 远端 .env 自动生成（JWT/WX/管理员凭据），敏感信息不推送到代码仓库

## [1.41.0] - 2026-08-09

### Added

- 新增 Server 部署方案（Docker + HF Space）：
  - 创建多阶段 Dockerfile（builder + runtime，镜像体积约 300MB）
  - 创建 docker-compose.yml（含数据卷持久化，默认端口 8000）
  - 创建 .dockerignore（排除 .venv、tests、__pycache__ 等）
  - 创建 docker-entrypoint.sh（启动时自动执行 alembic upgrade head）
  - 创建 .github/workflows/deploy-server-hf.yml（GitHub Actions 自动部署）
  - 创建 server/scripts/deploy-hf.sh（HF Space 部署脚本）
  - 创建 server/.env.hf.example（HF Space 环境变量模板）
  - 创建 server/spaces/README.md（HF Space 部署完整指南）
  - 创建 docs/plans/63-Server部署方案-Docker与HF-Space.md（方案文档）
- 部署脚本通过 HF API 设置 Secrets，敏感信息不推送到 git repo
- 环境变量校验：检测 GitHub Actions 环境，校验必需 Secrets 是否配置
- JWT_SECRET 生成命令文档（python/openssl 两种方式）

## [1.40.5] - 2026-08-09

### Fixed

- 修复 Admin 端 API 直连问题：移除代理配置，生产构建使用相对路径直连后台
- 修复 Admin 端支持生产环境子路径部署，login 路由使用 `VITE_ADMIN_BASE` 环境变量
- 修复 Admin 端 `VITE_API_BASE_URL` 环境变量配置，dev 模式通过 proxy 转发，生产模式直连

## [1.40.4] - 2026-08-09

### Fixed

- 修复事件日志 trace_id 不一致问题：登录、体重、装备、日记的原子操作（开始→成功/失败）现在使用同一个 trace_id，便于链路追踪

## [1.40.3] - 2026-08-09

### Fixed

- 修复 LineChart 组件使用 `getCurrentInstance().proxy` 替代 `this`，解决 Canvas 节点查询失败的问题

## [1.40.2] - 2026-08-09

### Fixed

- 修复 LineChart 组件在小程序中 SVG 路径数据未正确渲染的问题（改回 Canvas 2D 并使用 `this` 上下文）

## [1.40.1] - 2026-08-09

### Fixed

- 修复 LineChart 组件 X 轴标签 `wx:else` 编译错误（改用 `<template>` 包裹）

## [1.40.0] - 2026-08-09

### Changed

- LineChart 组件从 Canvas 2D 迁移到 SVG，解决小程序自定义组件中节点获取失败的问题

## [1.39.4] - 2026-08-09

### Fixed

- 修复统计页面体重趋势折线图不显示的问题（改用 setTimeout 确保 canvas 节点完全挂载）

## [1.39.3] - 2026-08-09

### Fixed

- 修复统计页面体重趋势折线图不显示的问题（使用双重 nextTick 确保 canvas 节点就绪）

## [1.39.2] - 2026-08-09

### Fixed

- 移除「我的」页面重复的编辑资料入口

## [1.39.1] - 2026-08-09

### Fixed

- 修复 LineChart 组件使用 `getCurrentInstance()` 在小程序环境中返回 null 导致 `$scope` 报错的问题

## [1.39.0] - 2026-08-09

### Added

- 事件日志新增 `trace_id` 和 `action` 独立字段，`extra` 只保留业务 payload
- 业务动作类型统一为 `business`，网络错误为 `network`，崩溃为 `crash`
- 管理端事件日志新增 `action` 搜索框和表格列
- 事件日志支持按 `trace_id` 和 `action` 精确过滤
- 小程序业务动作埋点覆盖：登录、资料更新、日记 CRUD、装备 CRUD、体重 CRUD
- 埋点携带精确操作时间 `client_time`（毫秒时间戳）和唯一操作链路 ID `trace_id`

### Fixed

- 修复头像上传后响应解析失败导致头像不更新的问题
- 修复编辑日记/装备时因 `editingId` 非响应式导致保存变成新增的问题
- 修复 form.vue 中 `ref` 未导入导致编译错误
- 修复 Admin 端日记/装备/体重创建时间显示 1970 年问题（时间戳类型不匹配）
- 修复 Admin 端创建时间显示精度，改为显示时分秒
- 修复日记/装备/体重列表排序问题：按创建时间倒序排列（原按 date/id）
- 修复事件日志上报时 dict 类型无法存入 SQLite Text 列的报错
- 修复事件日志响应序列化错误（extra/device_info 需 JSON 解析，created_at 需转 float）

## [1.38.0] - 2026-08-08

### Added

- 新增 Admin 前端 toast 提示组件（`stores/toast.ts` + `components/common/Toast.vue`），支持 success/error/warning/info 四种类型
- API 拦截器自动显示错误提示：业务错误 code!==0、HTTP 401/403/404/500 均自动弹出 toast
- 优化用户详情模态框布局：头像居中、信息卡片式展示、OpenID 脱敏、性别/时间格式化
- 新增 Admin 前端 `posts.ts` 和 `checkins.ts` API 模块

### Fixed

- 修复 Admin 前端 API 类型定义与后端 schema 不匹配问题：`feelings`→`feeling`、`photos`→`photo`、`body_fat`→`bust/waist/hip`、`type`→`kind`、`report`→`summary`
- 修复用户头像相对路径问题：`avatars/` → `avatar/`，拼接完整 URL
- 修复角色管理按钮不可点击问题：移除前端 `disabled` 限制，由后端保护系统角色
- 修复角色弹窗未重置问题：新建/编辑/关闭时清空表单

### Changed

- 更新文档状态与实际进度对齐（README/AGENTS/docs/plans）
- 精简 AGENTS.md（387行→114行）

## [1.37.0] - 2026-08-08

### Added

- 实现系统运行时长显示：`/api/admin/system/health` 接口的 `uptime` 字段从 "unknown" 改为真实运行时长，格式化为 "X天X小时X分钟X秒"

### Fixed

- 修复系统健康检查数据库连通性检测报错：`db.execute("SELECT 1")` 改为 `db.execute(text("SELECT 1"))`，适配 SQLAlchemy 2.0+

## [1.36.0] - 2026-08-08

### Added

- 统一后台API响应格式：所有接口返回 `{code, message, success, data}` 四字段
  - 新增 `schemas/common.py` 定义 `ApiResponse<T>`、`PaginatedData<T>`、`ErrorCode`
  - 注册全局异常处理器（HTTPException/ValidationError/Exception），自动转换为统一格式
  - 改造用户端路由（auth/diaries/gears/weights/checkin/stats/upload）
  - 改造 Admin 路由（auth/users/diaries/gears/weights/checkins/analyses/posts/roles/admins/system）
  - Admin 前端拦截器判断 `code===0` 返回 data，否则 reject
  - Miniapp 前端拦截器判断 `code===0` 返回 data，否则显示 toast

### Changed

- 错误码规范：0=成功，10000-19999=认证授权，20000-29999=参数校验，30000-39999=业务逻辑，50000-59999=服务器内部错误

## [1.35.0] - 2026-08-08

### Added

- 新增后台管理前端（Phase Admin 全部完成）：
  - 项目初始化（Vite + Vue 3 + TypeScript + Tailwind CSS）
  - 实现主布局（侧边栏、头部、面包屑）
  - 实现登录页（账号密码登录）
  - 实现仪表盘（数据概览卡片、系统状态）
  - 实现用户管理页面（列表、查看、删除）
  - 实现角色管理页面（列表、新建、编辑、删除、权限配置）
  - 实现管理员管理页面（列表、新建、编辑、重置密码、启用/禁用、删除）
  - 实现日记管理页面（列表、删除）
  - 实现装备管理页面（列表、删除）
  - 实现体重管理页面（列表、删除）
  - 实现分析报告页面（列表、查看、删除）
  - 实现系统监控（健康检查、日志查看、备份管理）
  - 通用组件（Table、Pagination、Modal、StatCard）
  - 配置 Nginx 和 Docker 部署

## [1.34.0] - 2026-08-08

### Added

- 新增系统监控管理API与日志分离（Phase B2-3）：
  - 新增日志分离功能（admin.log/user.log/app.log）
  - 支持结构化JSON日志输出
  - 新增请求日志中间件（自动识别admin/user请求）
  - 实现系统健康检查增强接口（数据库连通性/磁盘使用/运行时长）
  - 实现运行时指标接口（各表数据量/数据库大小）
  - 实现日志查询接口（按文件/级别/关键字过滤）
  - 实现数据库备份接口（SQLite在线备份）
  - 实现备份列表接口
  - 实现数据恢复接口（含自动备份当前库）
  - 完成测试用例（6 个测试全部通过）

## [1.33.0] - 2026-08-08

### Added

- 新增数据查看管理API（Phase B2-2）：
  - 实现用户管理接口（列表/详情/删除），支持分页
  - 实现日记管理接口（列表/详情/删除），支持分页和用户筛选
  - 实现装备管理接口（列表/详情/删除），支持分页和用户筛选
  - 实现体重管理接口（列表/删除），支持分页和用户筛选
  - 实现打卡管理接口（列表/删除），支持分页和用户筛选
  - 实现分析管理接口（列表/详情/删除），支持分页和用户筛选
  - 实现发布管理接口（列表/详情/删除），支持分页和用户筛选
  - 新增分页响应模型（`PaginatedResponse`）
  - 新增管理端响应模型（用户/日记/装备/体重/打卡/分析/发布）
  - 完成测试用例（4 个测试全部通过）

## [1.32.0] - 2026-08-08

### Added

- 新增角色权限系统与管理员管理功能（Phase B2-1）：
  - 新增 `Role` 模型与 `Admin` 模型（含 `role_id` 外键关联）
  - 实现权限常量定义（`permissions.py`），包含用户/数据/系统/管理员/角色管理共 30+ 权限
  - 实现初始角色数据初始化（超级管理员/普通管理员/只读管理员）
  - 实现管理员认证（登录/获取信息/修改密码），使用独立 JWT 密钥
  - 实现角色管理接口（CRUD + 权限列表）
  - 实现管理员管理接口（列表/创建/编辑/重置密码/启用禁用/删除）
  - 新增权限校验依赖（`require_permission`），支持细粒度权限控制
  - 新增 Alembic 迁移脚本（`add roles and admins tables`）
  - 完成测试用例（14 个测试全部通过）

## [1.31.3] - 2026-08-08

### Fixed

- 修复头像显示 401 Unauthorized：`GET /api/upload/avatar/{user_id}/{filename}` 原先要求 JWT 鉴权，但微信 `<image>` 组件无法携带 Authorization header，导致每次展示头像都触发 401。移除该 GET 端点的 `Depends(get_current_user)`，改为公开访问（URL 含 user_id + UUID 文件名，不可猜测，安全性足够）

## [1.31.2] - 2026-08-08

### Fixed

- 修复小程序登录失败时 toast 误弹无意义 "request:ok"：`services/request.ts` 的 `parseDetail` 去掉 `res.errMsg` 兜底（`uni.request` success 回调中 `errMsg` 恒为 "request:ok"，与 HTTP 状态码无关），改为优先取后端 `detail`/`message` → 非 JSON 文本 → 基于状态码的 `请求失败（HTTP 4xx/5xx）` 通用提示（见方案 41）
- 修复登录接口 401 误触发登出引导：`services/auth.ts` 的 `login()` 传 `handle401: false`，登录失败（如 code 过期）不再弹「请到『我的』页登录后使用」，由调用方直接展示真实错误（见方案 41）
- 修复登录成功后「我的」页昵称误显「未登录」：新注册用户后端 `nickname` 默认为空串，`mine.vue` 旧逻辑 `nickname || "未登录"` 兜底误判；改为新增 `profileName` computed，未登录显示「未登录」、已登录昵称为空显示「微信用户」（见方案 42）

## [1.31.0] - 2026-08-07

### Added

- 我的页与资料详情页 tarot 化改造（见方案 40）：`mine.vue` 用户卡升级为深橄榄渐变 + 青柠光斑，登录后展示累计打球/时长/装备三列统计徽章（`getStats`，失败静默降级 0），功能入口改为「图标 + 标签 + 箭头/开关」卡片式菜单（统计总览 `switchTab` / 编辑资料 / 金额隐私 / 青柠主题），退出登录移除并移入资料详情页，未登录隐藏功能菜单仅保留「微信一键登录」唯一入口且不发 `/stats` 请求；`profile-edit.vue` 居中大头像（小程序 `chooseAvatar` + H5 `chooseImage` 降级）、细分隔线表单、每字段自动保存（昵称 `blur/confirm`、性别/生日 `picker change`，成功轻提示）、底部独立「退出登录」确认后回「我的」Tab

## [1.30.1] - 2026-08-07

### Fixed

- 修复全项目 Tailwind 自定义色未生成导致界面无品牌色：`vite.config.ts` 中 `cssEntries` 原指向 `src/App.vue`（Vue 组件），weapp-tailwindcss 解析不到其 scss 内的 `@tailwind` 指令，回退默认 config，`bg-olive`/`from-olive`/`via-olive-mid` 等自定义色类未生成到 WXSS，所有页面纯白无层次。改为新建独立 `src/app.css`（含 `@config "../tailwind.config.js"` 显式指定 config 路径 + `@tailwind base/components/utilities`）、`App.vue` 非 scoped `@import '@/app.css'`、`cssEntries`/`tailwindcssBasedir` 修正（对齐 tarot 集成方式），全项目 olive/lime/paper 品牌色类恢复（见方案 40）

## [1.30.0] - 2026-08-07

### Added

- 后端接入 Alembic 数据库迁移（见方案 39）：新增 `alembic.ini` 与 `alembic/` 骨架，`env.py` 复用应用配置 `DATABASE_URL` 与 `Base.metadata`；生成基线迁移 `3a79ce8c1f19_initial_schema.py`（全部 7 张表 + `users.gender/birthday`）；`app/models/__init__.py` 集中导出全部模型；`pyproject.toml` 新增 `alembic` 依赖并对 `alembic/versions/*` 配置 ruff `per-file-ignore` 与 `format exclude`；新增 `test_models_registry.py` 校验模型注册与元数据完整性。此后模型字段变更一律走 `alembic revision --autogenerate` + `upgrade head`，严禁手工 `create_all`

## [1.29.0] - 2026-08-07

### Added

- 用户资料编辑与登录时序修复（参考 tarot，见方案 38）：`/api/auth/login` 一次返回 `{ access_token, user, is_new }`（修复「一键登录返回 token 后仍提示请先登录」的未登录短路 bug），新增 `PUT /api/auth/me` 更新用户资料（昵称/头像/性别/生日，仅更新传入字段）与 `POST /api/upload/avatar` 头像上传，`users` 表新增 `gender`/`birthday` 列；前端新增「编辑资料」页（`profile-edit`），「我的」页用户卡可点击进入并展示脱敏 ID/性别/生日，新增 `updateProfile`/`uploadAvatar`/`resolveUploadUrl`/`maskMiddle` 等工具与对应测试

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
