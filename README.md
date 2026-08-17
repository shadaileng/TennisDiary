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
│   ├── data/               # 运行时数据（SQLite + 上传文件，不纳入版本管理）
│   ├── scripts/            # 脚本（verify.sh / 部署脚本 docker/hf/oci/modelscope）
│   ├── modelscope/         # 魔搭创空间部署配置（ms_deploy.json + 专属 Dockerfile）
│   ├── oci/                # Oracle Cloud 部署指南
│   ├── spaces/             # HF Space 部署说明
│   ├── Dockerfile          # 生产镜像（多阶段）
│   ├── docker-compose.yml  # 本地一键启动（含数据卷持久化）
│   └── pyproject.toml      # uv 项目配置
├── miniapp/                # uni-app 小程序前端
│   └── src/
│       ├── components/     # 自定义组件
│       ├── config/         # 环境变量配置
│       ├── constants/      # 常量（含 storage 键名收口）
│       ├── pages/          # 页面
│       ├── services/       # 网络层（uni.request + JWT）
│       ├── stores/         # Pinia 状态管理
│       ├── styles/         # 全局样式
│       ├── types/          # 类型定义
│       ├── utils/          # 工具函数
│       ├── pages.json      # 路由 + TabBar
│       └── manifest.json   # 应用配置
├── admin/                  # 后台管理前端（Vite + Vue 3 + Tailwind）
├── proxy/                  # Cloudflare Workers 反向代理（魔搭 CORS + 鉴权头透传）
├── docs/                   # VitePress 文档站点
│   ├── plans/              # 方案文档
│   └── guides/             # 指南
├── .github/workflows/      # CI（当前仅 modelscope 部署启用）
└── package.json            # pnpm workspace 根配置
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

- [Server 文档](server/README.md) - 后端服务启动、数据库迁移、常用命令
- [方案文档](docs/README.md) - 各阶段方案与进度（VitePress 文档中心）
- [开发指南](docs/guides/) - VitePress 踩坑记录等

本地查看：`pnpm docs:dev` 后访问 VitePress 站点。

## 进度

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
| Phase 67  | Cloudflare Workers 反向代理（解决魔搭网关 CORS + 鉴权头透传） | ✅ |
| 75-B2-Admin | Admin 同步 AI 网关三件套（分析详情六维报告 + ai-status/ai-connect + 健康页 AI 卡片） | ✅ |
| 75-1~6 | AI 评分代理 / 视频上传抽帧 / MediaPipe 姿态推理 / 分析报告落库 / 电子教练页 / 分享工坊 | ✅ |
| 78 | 动态配置系统与 Admin 配置页（注册表 7 分类 20 项 + system_configs 覆盖表 + AI 三件套在线配置） | ✅ |
| 79 | AI 服务商管理与配置直选（ai_providers 表 + ai.provider 引用，模型可独立覆盖） | ✅ |
| 80 | AI 服务商多模型支持（models 列表 + 服务商→模型二选下拉，ai.model 覆盖全局优先） | ✅ |

详细进度与方案索引见 `docs/plans/` 目录。

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

前端环境变量见 `miniapp/.env.example`（`VITE_API_BASE_URL` / `VITE_REQUEST_TIMEOUT` / `TD_APPID` / `TD_URL_CHECK`）。

| 变量 | 说明 | 默认值 |
|---|---|---|
| `VITE_API_BASE_URL` | 后台 API base URL（运行期，`import.meta.env`） | `http://127.0.0.1:8000` |
| `VITE_REQUEST_TIMEOUT` | 请求超时（毫秒） | `10000` |
| `TD_APPID` | 微信小程序 AppID（构建期注入 `project.config.json`，部署小程序必填） | — |
| `TD_URL_CHECK` | 域名白名单校验开关（`false` 开发 / `true` 生产，写入 `setting.urlCheck`） | `false` |

前端构建期变量（`TD_*`，非 `VITE_` 前缀）由 `vite.config.ts` 在构建时读取，不进入 `import.meta.env` / 打包产物。

### 小程序环境配置

```bash
cd miniapp
cp .env.example .env      # 填写 TD_APPID 等
pnpm build:mp-weixin      # 构建，appid 与 urlCheck 自动写入 dist/build/mp-weixin/project.config.json
```

- 所有 `.env*` 文件均被 `.gitignore` 忽略，不提交（仅保留 `.env.example` 模板）
- 不同环境可创建 `.env.development` / `.env.production` 覆盖
- 微信小程序要求 `request` 合法域名必须为**已备案 HTTPS 域名**，需在 [微信公众平台](https://mp.weixin.qq.com)「开发管理 → 开发设置 → 服务器域名」中配置 request/uploadFile/downloadFile 合法域名；`TD_URL_CHECK=true` 后开发者工具将强制校验
