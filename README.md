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
| 微信小程序前端 | uni-app（Vue 3 + Vite + TypeScript）+ Pinia + Vant 4 + Tailwind CSS |
| H5 前端（测试用） | 同上，编译到 H5 用于后端 API 联调 |
| 后端 | FastAPI（Python 3.10+）+ SQLite + SQLAlchemy |
| 依赖管理 | uv |
| 文档 | VitePress |

## 目录结构

```
workspace/
├── server/            # FastAPI 后台服务
│   ├── app/
│   │   ├── main.py         # 入口
│   │   ├── core/           # 配置、数据库连接、鉴权
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── routers/        # API 路由
│   │   ├── schemas/        # Pydantic 数据模型
│   │   └── services/       # 业务逻辑
│   ├── data/               # SQLite 数据文件
│   ├── uploads/            # 用户上传文件
│   └── pyproject.toml      # uv 项目配置
├── miniapp/                # uni-app 小程序前端（待创建）
├── docs/                   # VitePress 文档站点
│   ├── plans/              # 方案文档
│   └── guides/             # 指南
└── package.json            # 文档站点依赖
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
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs 查看 API 文档
```

## 文档

- [项目分析报告](https://cnb.cool/...) - Tennis Diary 迁移微信小程序可行性分析
- [执行方案](https://cnb.cool/...) - 各阶段详细实施步骤
- [开发指南](https://cnb.cool/...) - VitePress 踩坑记录等

本地查看：`pnpm docs:dev` 后访问 VitePress 站点。

## 进度

当前阶段：**Phase B1 — FastAPI 后台脚手架 + 数据层**

| Step | 内容 | 状态 |
|------|------|:----:|
| B1-1 | 项目初始化与目录结构 | ✅ |
| B1-2 | 核心配置模块 | ✅ |
| B1-3 | 数据库模型（7 张表） | ✅ |
| B1-4 | Pydantic Schemas | ⬜ |
| B1-5 | 微信登录鉴权 | ⬜ |
| B1-6~11 | CRUD 接口 + 入口组装 | ⬜ |

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
