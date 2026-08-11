# AGENTS — AI 协作者指南

本文档面向在此项目中工作的 AI 协作者，提供项目上下文和协作规范。

## 项目概览

- **项目名称**：Tennis Diary（网球日记）
- **目标**：将 Tennis Diary Web 版（React PWA）迁移为微信小程序（uni-app + FastAPI）
- **方案文档**：`docs/plans/` 目录，编号 `{序号}-{标题}.md`
- **参考源码**：`docs/reference/tennis-diary/`（原 Web 版，不纳入版本管理）

## 技术栈

| 端 | 技术 |
|---|---|
| 小程序前端 | uni-app（Vue 3 + Vite + TypeScript）+ Pinia + Tailwind CSS（自定义组件） |
| 后端 | FastAPI（Python 3.10+）+ SQLite + SQLAlchemy |
| 依赖管理 | uv（后端）、pnpm（前端/文档） |
| Node 运行时 | **≥ 22.12（建议 24 LTS）**，根目录 `.nvmrc` 固定 `24` |
| 文档 | VitePress |

## 项目结构

```
workspace/
├── server/            # FastAPI 后台（含部署：Docker/oci/modelscope/spaces）
├── miniapp/           # uni-app 小程序前端
├── admin/             # 后台管理前端（Vite + Vue 3）
├── proxy/             # Cloudflare Workers 反向代理（解决魔搭 CORS + 鉴权头透传）
├── docs/
│   └── plans/         # 方案文档（执行索引）
├── .github/
│   ├── workflows/                 # 启用的 CI（当前仅 modelscope 部署）
│   └── workflows-disabled/        # 停用的 CI（HF/OCI 部署，待启用）
├── package.json       # pnpm workspace 根配置
└── pnpm-workspace.yaml
```

## 工作流程

### TDD 模式

1. **写方案文档**：`docs/plans/{编号}-{标题}.md`
2. **RED**：写测试，确认失败
3. **GREEN**：写最小代码使测试通过
4. **REFACTOR**：优化结构，保持测试通过
5. **完成**：方案状态 `📋` → `✅`

### 常用命令

```bash
# 后端
cd server && uv run pytest -v          # 测试
cd server && uv run ruff check .       # lint
cd server && uv run ruff format .      # 格式化
cd server && bash scripts/verify.sh    # 一键验证

# 前端
cd miniapp && pnpm build:mp-weixin     # 构建小程序
cd admin && pnpm build                 # 构建管理端
```

### 提交规范

```
<type>(<scope>): <中文描述>
```

- `feat`：新功能（自动 bump 次版本号）
- `fix`：修复（自动 bump 修订号）
- `docs` / `chore`：文档 / 依赖配置

禁止 `git add .`，禁止无意义消息（`wip`、`tmp`）。

## 编码规范

### 后端

- ORM：SQLAlchemy 声明式，继承 `app.core.database.Base`
- Schema：Pydantic models，定义在 `app/schemas/`
- 路由：`APIRouter`，统一前缀 `/api/`
- 鉴权：所有数据接口依赖 `get_current_user`
- 启动：`cd server && uv run uvicorn app.main:app --reload`

### 前端

- Vue 3 Composition API + `<script setup>`
- 状态管理：Pinia
- 样式：Tailwind CSS（`weapp-tailwindcss`，`rem2rpx` 转换）
- 组件：Tailwind 自定义组件（`src/components/`）
- 环境变量：运行期 `VITE_*`，构建期非 `VITE_` 前缀（`vite.config.ts` 插件注入）

## API 规范

### 统一响应格式

```json
// 成功
{"code": 0, "message": "ok", "success": true, "data": {...}}

// 失败
{"code": 10001, "message": "未登录", "success": false, "data": null}
```

**错误码**：0=成功 | 10000-19999=认证授权 | 20000-29999=参数校验 | 30000-39999=业务逻辑 | 50000-59999=服务器错误

### 鉴权

- 登录：`POST /api/auth/login`，接收 `wx.login` code，返回 JWT
- 请求头：`X-Auth-Token: <jwt>`（魔搭网关占用 `Authorization`，统一改用自定义头）
- 有效期：30 天

### 端点概览

详见 `docs/plans/` 中各方案文档，或启动服务后访问 `/docs`（Swagger）。

- **用户端**：`/api/auth/*`、`/api/diaries`、`/api/gears`、`/api/weights`、`/api/checkin`、`/api/stats`、`/api/files/*`、`/api/upload/*`、`/api/events`
- **管理端**：`/api/admin/auth/*`、`/api/admin/roles`、`/api/admin/admins`、`/api/admin/users`、`/api/admin/diaries`、`/api/admin/gears`、`/api/admin/weights`、`/api/admin/checkins`、`/api/admin/analyses`、`/api/admin/posts`、`/api/admin/system/*`、`/api/admin/events`

## 项目进度

| 阶段 | 内容 | 状态 |
|------|------|:----:|
| Phase B1 | 后台基础接口（11个） | ✅ |
| Phase B2 | 后台管理API（角色/权限/管理员/数据查看/系统监控） | ✅ |
| Phase Admin | 后台管理前端（Vite+Vue3+Tailwind） | ✅ |
| Phase 1 | 小程序基础能力（工程/Tailwind/store/网络/登录） | ✅ |
| Phase 2 | 小程序业务页面（日记/装备/统计/我的） | ✅ |
| Phase 2.5 | 小程序视觉样式与交互适配 | ✅ |
| Phase 2.6 | 小程序样式方案重构（Tailwind→自定义 CSS） | ✅ |
| Phase 2.7 | 输入框与空状态样式优化 | ✅ |
| Phase 59  | 事件锚点与线上事件日志（小程序埋点 + 后台查询 + 管理端页面） | ✅ |
| Phase 61  | 构建警告修复（Sass @import → additionalData + 循环依赖） | ✅ |
| Server-1  | Server 部署方案（Docker + HF Space，代码已实现；HF 已停用） | ⏳ 已归档 |
| Server-2  | Server 部署方案（Oracle Cloud Always Free 免费 VM，代码已实现；待建 VM 启用 CI） | ✅ |
| Server-3  | Server 部署方案（魔搭创空间 ModelScope Studio，代码已实现；当前启用） | ✅ |
| Phase 66  | ModelScope 部署鉴权头兼容改造（后端统一 `X-Auth-Token`，移除 `Authorization` 回退） | ✅ |
| Phase 67  | Cloudflare Workers 反向代理（解决魔搭网关 CORS 预检 + `X-Auth-Token` 透传） | ✅ |
| Fix 2026-08-10 | 小程序表单保存防重复提交、`safeNavigateBack` 栈底回退、`eventLogger` 移除 `require()` 别名解析 | ✅ |
| Phase 68 | Admin 全局 Loading 遮罩（axios 拦截器请求计数器）与提交类操作防重复提交（`useActionLock`） | ✅ |

> 说明：三个 Server 部署方案的脚本/指南/CI/env 模板均已完成。当前唯一启用的部署 CI 为 `deploy-server-modelscope.yml`（魔搭）；HF（需 PRO 订阅）与 OCI（待建 VM）的 workflow 位于 `.github/workflows-disabled/`。详细见 `docs/plans/63/64/65-*`。

详细进度与方案索引见 `docs/plans/` 目录。

## 注意事项

- **Node ≥ 22.12**：低于此版本 `@weapp-tailwindcss/postcss` 无法 `require()` ESM 包
- **config.py 路径**：`Path(__file__).resolve().parent.parent.parent / ".env"`（向上三级到 `server/`）
- **数据库迁移**：用 Alembic，禁止 `create_all`；新增模型须在 `app/models/__init__.py` 登记
- **SQLite 数据文件**：不纳入版本管理（已 `.gitignore`）
- **生产环境**：`request` 合法域名必须已备案，需 Nginx 反代
