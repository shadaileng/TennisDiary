# Tennis Diary（网球日记）

面向网球爱好者的 AI 辅助训练记录与动作分析应用。

## 项目简介

Tennis Diary 帮助网球爱好者：
- **结构化记录打球数据**：日记、装备、体重、打卡统计
- **AI 动作分析**：上传挥拍视频，获得六维评分 + NTRP 等级评估
- **社媒分享**：自动生成分享卡片和文案

本项目是 Tennis Diary **Web 版（React PWA）** 向**微信小程序版（uni-app + FastAPI）** 的迁移工程。

## 技术栈

| 端 | 技术 |
|---|---|
| 微信小程序前端 | uni-app（Vue 3 + Vite + TypeScript）+ Pinia + Tailwind CSS（自定义组件，替代 Vant） |
| 后端 | FastAPI（Python 3.10+）+ SQLite + SQLAlchemy |
| 依赖管理 | uv（后端）、pnpm（前端/文档） |
| 文档 | VitePress |

## 目录结构

```
workspace/
├── server/                 # FastAPI 后台服务
│   ├── app/
│   │   ├── main.py         # 入口
│   │   ├── core/           # 配置、数据库连接、鉴权、日志
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── routers/        # API 路由
│   │   ├── schemas/        # Pydantic 数据模型
│   │   └── services/       # 业务逻辑
│   ├── tests/              # pytest 测试（镜像 app/ 结构）
│   ├── data/               # SQLite 数据文件
│   ├── uploads/            # 用户上传文件
│   ├── scripts/verify.sh   # 一键验证（ruff + pytest）
│   └── pyproject.toml      # uv 项目配置
├── miniapp/                # uni-app 小程序前端
│   └── src/
│       ├── components/     # Tailwind 自定义组件
│       ├── config/         # 环境变量配置
│       ├── constants/      # 常量（含 storage 键名收口）
│       ├── pages/          # 页面
│       ├── services/       # 网络层（uni.request + JWT）
│       ├── stores/         # Pinia 状态管理
│       ├── styles/         # 全局样式 / Tailwind
│       ├── types/          # 类型定义
│       ├── utils/          # 工具函数
│       ├── pages.json      # 路由 + TabBar
│       └── manifest.json   # 应用配置
├── docs/                   # VitePress 文档站点
│   ├── plans/              # 方案文档
│   └── guides/             # 指南
└── package.json            # 文档站点依赖（pnpm workspace）
```

## 快速开始

### 文档站点

```bash
pnpm install
pnpm docs:dev
# 访问 http://localhost:5173
```

### 后台服务

```bash
cd server
uv sync
cp .env.example .env   # 填写 WX_APPID、WX_SECRET 等必填项
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs 查看 API 文档
```

### 小程序前端

```bash
cd miniapp
pnpm install
pnpm dev:h5          # H5 联调
pnpm dev:mp-weixin   # 微信开发者工具导入 miniapp/dist/dev/mp-weixin
```

## 文档

- [方案文档](docs/README.md) - 各阶段方案与进度（VitePress 文档中心）
- [开发指南](docs/guides/) - VitePress 踩坑记录等

本地查看：`pnpm docs:dev` 后访问 VitePress 站点。

## 进度

当前阶段：**Phase B1 后台基础接口已完成，Phase 1 小程序前端基础能力已完成**

### Phase B1 — FastAPI 后台

| Step | 内容 | 状态 |
|------|------|:----:|
| B1-1 | 项目初始化 | ✅ |
| B1-2 | 核心配置模块 | ✅ |
| B1-3 | 数据库模型 | ✅ |
| B1-4 | 日志系统（loguru）+ Pydantic Schemas | ✅ |
| B1-5 | 微信登录鉴权（auth 路由 + core/auth + wx_service） | ✅ |
| B1-6 | 日记 CRUD `/api/diaries` | ✅ |
| B1-7 | 装备 CRUD `/api/gears` | ✅ |
| B1-8 | 体重记录 `/api/weights` | ✅ |
| B1-9 | 打卡 `/api/checkin` | ✅ |
| B1-10 | 统计汇总 `/api/stats` | ✅ |
| B1-11 | 文件下载 `/api/files/{filename}` | ✅ |

### Phase 1 — 小程序前端

| Step | 内容 | 状态 |
|------|------|:----:|
| Phase1-1 | uni-app 工程初始化（Vue3 + Vite + TS） | ✅ |
| Phase1-2 | 目录结构 + TabBar + 占位页 | ✅ |
| Phase1-3 | Tailwind CSS 集成（主题色） | ✅ |
| Phase1-4 | Tailwind 自定义组件（替代 Vant） | ✅ |
| Phase1-5 | `types.ts` 类型迁移 | ✅ |
| Phase1-6 | Pinia store 搭建 | ✅ |
| Phase1-7 | 网络层封装（`uni.request` + JWT） | ✅ |
| Phase1-8 | 对接 B1 登录流程 | ✅ |
| 21 | 前后端 `.env` 配置模板 + storage 键名收口 | ✅ |

## 环境变量

后台服务通过环境变量配置，复制模板并填写：

```bash
cp server/.env.example server/.env
# 编辑 server/.env，填写 WX_APPID、WX_SECRET 等必填项
```

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATA_DIR` | 运行时数据根目录 | `./data` |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/tennis_diary.db` |
| `UPLOAD_DIR` | 文件上传目录 | `./data/uploads` |
| `DEBUG` | 调试模式 | `false` |
| `JWT_SECRET` | JWT 密钥 | — |
| `WX_APPID` | 微信小程序 AppID | — |
| `WX_SECRET` | 微信小程序 Secret | — |
| `AI_API_KEY` | AI API Key | — |

前端环境变量见 `miniapp/.env.example`（`VITE_API_BASE_URL` / `VITE_REQUEST_TIMEOUT`）。
