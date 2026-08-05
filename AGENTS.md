# AGENTS — AI 协作者指南

本文档面向在此项目中工作的 AI 协作者（如 Claude、CodeBuddy 等），提供项目上下文和协作规范。

## 项目概览

- **项目名称**：Tennis Diary（网球日记）
- **目标**：将 Tennis Diary Web 版（React PWA）迁移为微信小程序（uni-app + FastAPI）
- **主计划文档**：`docs/plans/01-tennis-diary-迁移微信小程序分析.md`
- **参考源码**：`docs/reference/tennis-diary/`（原 Web 版源码，不纳入版本管理）

## 技术栈

| 端 | 技术 |
|---|---|
| 小程序前端 | uni-app（Vue 3 + Vite + TypeScript）+ Pinia + Vant 4 + Tailwind CSS |
| 后端 | FastAPI（Python 3.10+）+ SQLite + SQLAlchemy |
| 依赖管理 | uv（后端）、pnpm（前端/文档） |
| 文档 | VitePress |

## 项目结构

```
workspace/
├── server/            # FastAPI 后台（Phase B1 实施中）
├── miniapp/           # uni-app 小程序前端（Phase 1 待创建）
├── docs/              # VitePress 文档站点
│   ├── plans/         # 方案文档（含执行方案）
│   └── guides/        # 指南
└── package.json       # 文档站点依赖
```

## 工作流程

### 实施方式

1. **每步先写方案文档**：在 `docs/plans/` 下创建 `{编号}-{标题}.md`，写明目标、步骤、产出物、验收标准
2. **按方案执行代码**：严格按照方案文档的步骤实施
3. **完成后更新状态**：方案文档状态从 `📋 待执行` → `✅ 已完成`

### 提交规范

遵循 Conventional Commits，使用中文描述：

```
<type>(<scope>): <中文描述>
```

类型判定：
- 新增功能/接口 → `feat`
- 修复错误 → `fix`
- 文档 → `docs`
- 依赖/配置 → `chore`

每次 `feat` 提交自动 bump `package.json` 次版本号。

### 原子提交

- 一个提交只做一件事
- 禁止 `git add .` 全量暂存
- 禁止无意义提交消息（如 `wip`、`tmp`）

## 编码规范

### 后端（Python / FastAPI）

- 使用 `uv` 管理依赖，配置在 `pyproject.toml`
- 数据库模型使用 SQLAlchemy 声明式 ORM，继承自 `app.core.database.Base`
- 请求/响应使用 Pydantic models，定义在 `app/schemas/schemas.py`
- 路由使用 FastAPI `APIRouter`，统一前缀 `/api/`
- 所有数据接口依赖 `get_current_user` 鉴权
- 启动命令：`uv run uvicorn app.main:app --reload`

### 前端（uni-app / Vue 3）— 待 Phase 1 细化

- 使用 Vue 3 Composition API + `<script setup>`
- 状态管理使用 Pinia
- 样式使用 Tailwind CSS（`tailwindcss-miniprogram-preset`）
- UI 组件优先使用 Vant 4
- 微信/浏览器差异通过 uni-app 条件编译（`#ifdef`）隔离

### 文档

- 文档编号格式：`{序号}-{中文标题}.md`
- 文档状态：📋 待执行 / 🚧 进行中 / ✅ 已完成
- 所有 `.md` 文件包含 YAML frontmatter 元信息块

## API 接口规范

### 鉴权

- 登录：`POST /api/auth/login`，接收 `wx.login` 的 `code`，返回 JWT
- 后续请求：`Authorization: Bearer <jwt>`
- Token 有效期：30 天

### 数据接口（Phase B1）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/auth/login` | POST | 微信登录 |
| `/api/diaries` | GET/POST | 日记列表/创建 |
| `/api/diaries/{id}` | GET/PUT/DELETE | 日记详情/编辑/删除 |
| `/api/gears` | GET/POST | 装备列表/添加 |
| `/api/gears/{id}` | GET/PUT/DELETE | 装备详情/编辑/删除 |
| `/api/weights` | GET/POST | 体重记录列表/添加 |
| `/api/weights/{id}` | DELETE | 删除体重记录 |
| `/api/checkin` | GET/POST | 打卡查询/签到 |
| `/api/stats` | GET | 统计数据汇总 |
| `/api/files/{filename}` | GET | 文件下载 |

### 数据结构

与参考源码 `docs/reference/tennis-diary/src/types.ts` 中定义一致：
- `Diary`：日记（日期/类型/时长/强度/心情/花费/装备/笔记）
- `Gear`：装备（种类/名称/购买日期/价格/感受/照片）
- `WeightRecord`：体重记录（日期/体重/围度）
- `Analysis`：动作分析报告
- `Checkin`：训练营打卡
- `Post`：社媒发布管理

## 当前状态

Phase B1 后台基础建设中：

| Step | 内容 | 状态 |
|------|------|:----:|
| B1-1 | 项目初始化 | ✅ |
| B1-2 | 核心配置 | ✅ |
| B1-3 | 数据库模型 | ✅ |
| B1-4 | Pydantic Schemas | ⬜ 下一步 |

## 注意事项

- 后台使用 `uv` 而非 `pip` 管理依赖
- SQLite 数据文件和上传文件不纳入版本管理（已 `.gitignore`）
- `docs/reference/` 目录已通过 `srcExclude` 排除在 VitePress 构建外
- 微信小程序要求 `request` 合法域名必须已备案，生产环境需自备域名 + Nginx 反代
