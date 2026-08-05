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
| 小程序前端 | uni-app（Vue 3 + Vite + TypeScript）+ Pinia + Tailwind CSS（自定义组件） |
| 后端 | FastAPI（Python 3.10+）+ SQLite + SQLAlchemy |
| 依赖管理 | uv（后端）、pnpm（前端/文档） |
| 文档 | VitePress |

## 项目结构

```
workspace/
├── server/            # FastAPI 后台（Phase B1 实施中）
├── miniapp/           # uni-app 小程序前端（Phase 1 实施中）
├── docs/              # VitePress 文档站点
│   ├── plans/         # 方案文档（含执行方案）
│   └── guides/        # 指南
└── package.json       # 文档站点依赖
```

## 工作流程

### 实施方式（TDD 模式）

1. **每步先写方案文档**：在 `docs/plans/` 下创建 `{编号}-{标题}.md`，写明目标、步骤、产出物、验收标准
2. **先写测试（RED）**：按验收标准编写测试用例，运行确认测试失败
3. **再写实现（GREEN）**：编写最小代码使测试通过
4. **重构（REFACTOR）**：优化代码结构，保持测试通过
5. **完成后更新状态**：方案文档状态从 `📋 待执行` → `✅ 已完成`

### TDD 规范

| 规范项 | 说明 |
|---|---|
| 测试框架 | **pytest** + **httpx**（FastAPI TestClient） |
| 测试目录 | `server/tests/`，镜像 `app/` 结构 |
| 命名规范 | 测试文件：`test_<模块名>.py`，测试函数：`test_<功能描述>` |
| 数据库隔离 | 每个测试模块使用独立 SQLite（`:memory:` 或临时文件），通过 fixture 注入 |
| 鉴权模拟 | 通过 `override_get_current_user` 覆盖依赖，免去真实微信 code2Session 调用 |
| 运行命令 | `cd server && uv run pytest -v` |
| 覆盖率要求 | 核心业务逻辑（routers / services / auth）覆盖率 ≥ 80% |

### 静态检查（ruff）

后台使用 **ruff** 做静态检查与格式化，已纳入验证体系：

| 命令 | 说明 |
|------|------|
| `cd server && uv run ruff check .` | 静态检查（import 排序、未用导入、类型注解等） |
| `cd server && uv run ruff format .` | 自动格式化 |
| `cd server && uv run ruff format --check .` | 仅检查格式是否符合规范 |
| `cd server && bash scripts/verify.sh` | **一键验证**：ruff check + ruff format 检查 + pytest |

ruff 配置位于 `server/pyproject.toml` 的 `[tool.ruff]`：
- 行宽 `line-length = 100`，目标版本 `py310`
- 启用规则：`E, F, I, UP, B, BLE, PIE, RUF`
- 忽略 `B008`（FastAPI `Depends()` 惯用法）与 `RUF001/002/003`（中文全角标点属正常用法）
- 测试文件忽略 `B` 类规则

提交后台代码前，建议先运行 `bash scripts/verify.sh` 确保 ruff 与 pytest 全部通过。

### 提交前钩子（pre-commit）

仓库内置 `.githooks/pre-commit`，仅在 `server/` 下有暂存改动时自动运行 ruff 检查 + 格式化检查 + pytest，任一步失败则阻止提交。

**启用（每个仓库克隆后执行一次）**：
```bash
git config core.hooksPath .githooks
```

启用后正常 `git commit` 即可自动触发；若需跳过验证可用 `git commit --no-verify`（不推荐）。

### 测试文件与源文件对应

```
server/
├── app/
│   ├── core/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dirs.py
│   │   └── logging.py
│   ├── models/
│   │   ├── user.py
│   │   └── diary.py
│   ├── routers/
│   │   ├── auth.py
│   │   └── diaries.py
│   └── ...
└── tests/
    ├── conftest.py              # 全局 fixture（test client、测试 DB、mock 用户）
    ├── core/
    │   └── test_auth.py         # JWT 签发/解码/鉴权测试
    ├── models/
    │   └── test_user.py         # User 模型 CRUD 测试
    └── routers/
        ├── test_auth.py         # /api/auth/login 接口测试
        └── test_diaries.py      # /api/diaries 接口测试
```

### TDD 循环示例

以 B1-5「微信登录鉴权」为例：

```
1. 写方案文档：明确 /api/auth/login 接口规格
2. RED：写 test_auth.py — test_login_with_valid_code / test_login_with_invalid_code / test_get_current_user
3. GREEN：实现 auth.py 路由 + core/auth.py 鉴权
4. REFACTOR：抽取 wx_service，优化错误处理
5. 全部测试通过 → 标记完成
```

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
- UI 用 Tailwind 自定义组件（放弃 Vant，原因见方案 16-Phase1-4）；需复用处抽到 `src/components/`
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

Phase B1 后台基础接口已全部完成，待开展小程序前端（Phase 1）：

| Step | 内容 | 状态 | 方案文档 |
|------|------|:----:|------|
| B1-1 | 项目初始化 | ✅ | 02-B1-1 |
| B1-2 | 核心配置 | ✅ | 03-B1-2 |
| B1-3 | 数据库模型 | ✅ | 04-B1-3 |
| B1-4 | 日志系统（loguru）+ Pydantic Schemas | ✅ | 05-B1-4 |
| B1-5 | 微信登录鉴权（auth 路由 + core/auth + wx_service） | ✅ | （并入 B1-4 日志文档） |
| B1-6 | 日记 CRUD 接口 `/api/diaries` | ✅ | 06-B1-6 |
| B1-7 | 装备 CRUD 接口 `/api/gears` | ✅ | 07-B1-7 |
| B1-8 | 体重记录接口 `/api/weights` | ✅ | 08-B1-8 |
| B1-9 | 打卡接口 `/api/checkin` | ✅ | 09-B1-9 |
| B1-10 | 统计汇总 `/api/stats` | ✅ | 10-B1-10 |
| B1-11 | 文件下载 `/api/files/{filename}` | ✅ | 11-B1-11 |
| B1 阶段 | 后台基础接口全部完成 | ✅ | — |

Phase 1 小程序前端（进行中）：

| Step | 内容 | 状态 | 方案文档 |
|------|------|:----:|------|
| Phase1 总纲 | uni-app 前端工程初始化方案 | 📋 | 12-Phase1 |
| Phase1-1 | uni-app 工程初始化（Vue3+Vite+TS） | ✅ | 13-Phase1-1 |
| Phase1-2 | 目录结构 + `pages.json` TabBar + 占位页 | ✅ | 14-Phase1-2 |
| Phase1-3 | Tailwind CSS 集成（主题色） | ✅ | 15-Phase1-3 |
| Phase1-4 | 组件方案：Tailwind 自定义组件（替代 Vant） | ✅ | 16-Phase1-4 |
| Phase1-5 | `types.ts` 类型迁移 | 📋 | — |
| Phase1-6 | Pinia store 搭建 | 📋 | — |
| Phase1-7 | 网络层封装（`uni.request` + JWT） | 📋 | — |
| Phase1-8 | 对接 B1 登录流程 | 📋 | — |

## 注意事项

- 后台使用 `uv` 而非 `pip` 管理依赖
- SQLite 数据文件和上传文件不纳入版本管理（已 `.gitignore`）
- `docs/reference/` 目录已通过 `srcExclude` 排除在 VitePress 构建外
- 微信小程序要求 `request` 合法域名必须已备案，生产环境需自备域名 + Nginx 反代
