# Tennis Diary Server

FastAPI 后台服务，提供小程序与管理端的所有 API。

## 技术栈

- **框架**：FastAPI + SQLAlchemy 2.0（声明式 ORM）
- **数据库**：SQLite（单文件，本地与生产 Docker 部署均使用）
- **迁移工具**：Alembic
- **依赖管理**：uv（`uv.lock` 已纳入版本管理）
- **测试**：pytest
- **代码质量**：ruff（lint + format）

## 快速启动

```bash
cd server
uv sync
cp .env.example .env   # 填写必要配置
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs 查看 API 文档
```

## 常用命令

```bash
# 运行测试
uv run pytest -v

# 代码检查
uv run ruff check .
uv run ruff format .

# 一键验证（lint + format + test）
bash scripts/verify.sh
```

## 数据库迁移（Alembic）

### 前置准备

1. 在 `app/models/` 下新增或修改 SQLAlchemy 模型
2. 将新模型导入 `app/models/__init__.py`，确保 `Base.metadata` 能发现所有表

### 迁移命令

```bash
# 进入 server 目录
cd server

# ① 生成迁移脚本（自动检测模型变更）
uv run alembic revision --autogenerate -m "描述变更内容"

# ② 检查生成的脚本，确认 diff 符合预期
#    文件位于 alembic/versions/ 目录

# ③ 执行迁移
uv run alembic upgrade head

# ④ 验证数据库状态
uv run alembic current
# 应显示最新 revision id
```

### 其他常用命令

| 命令 | 说明 |
|------|------|
| `uv run alembic heads` | 查看所有可用 revision |
| `uv run alembic history` | 查看迁移历史 |
| `uv run alembic upgrade <revision>` | 升级到指定版本 |
| `uv run alembic downgrade -1` | 回退一步 |
| `uv run alembic stamp head` | 标记数据库已最新（不执行 SQL） |

### 注意事项

- **禁止 `create_all`**：Alembic 负责建表，不允许在代码中直接 `Base.metadata.create_all()`
- **SQLite 兼容**：Alembic 自动检测 `sqlite:///` 路径，无需额外配置
- **迁移脚本幂等**：已执行的 migration 不会重复运行
- **生成脚本后先 review**：`autogenerate` 生成的脚本可能不够精确，需人工确认

## 项目结构

```
server/
├── alembic/           # 迁移脚本
│   ├── versions/      # 各版本迁移文件
│   └── env.py         # 迁移环境配置
├── app/
│   ├── core/          # 配置、数据库、鉴权、日志
│   ├── models/        # SQLAlchemy ORM 模型
│   ├── routers/       # API 路由
│   ├── schemas/       # Pydantic 数据模型
│   └── services/      # 业务逻辑
├── tests/             # pytest 测试（镜像 app/ 结构）
├── data/              # 运行时数据（SQLite + 上传文件，不纳入版本管理）
├── scripts/           # 运维/部署脚本（verify / docker-entrypoint / hf / oci / modelscope）
├── modelscope/        # 魔搭创空间部署（ms_deploy.json + 专属 Dockerfile + README）
├── oci/               # Oracle Cloud 部署指南
├── spaces/            # HF Space 部署说明
├── Dockerfile         # 生产镜像（多阶段构建）
├── docker-compose.yml # 本地一键启动（含数据卷持久化）
├── README.hf.md       # HF Space 前端配置（sdk: docker）
├── pyproject.toml     # uv 项目配置
├── uv.lock            # 依赖锁定（已纳入版本管理）
└── .env.example       # 环境变量模板
```

## 环境变量

复制 `.env.example` 到 `.env` 并填写必要配置：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATA_DIR` | 运行时数据根目录 | `./data` |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/tennis_diary.db` |
| `UPLOAD_DIR` | 文件上传目录 | `./data/uploads` |
| `DEBUG` | 调试模式 | `false` |
| `JWT_SECRET` | JWT 签名密钥 | — |
| `WX_APPID` | 微信小程序 AppID | — |
| `WX_SECRET` | 微信小程序 Secret | — |
| `AI_API_KEY` | AI API Key | — |

## 部署方案

项目提供三种 Server 部署方案，代码均已实现。当前**启用**魔搭方案，HF/OCI 的 CI 处于停用状态。

| 方案 | 目录 | CI | 状态 |
|------|------|:----:|:----:|
| Docker 本地 / 自有服务器 | `Dockerfile` + `docker-compose.yml` | — | ✅ 有效 |
| HF Space 免费托管 | `spaces/` + `README.hf.md` + `.env.hf.example` + `scripts/deploy-hf.sh` | `workflows-disabled/` | ⏳ 已停用（需 PRO 订阅） |
| Oracle Cloud 免费 VM | `oci/` + `scripts/{oci-bootstrap,deploy-oci}.sh` + `.env.oci.example` | `workflows-disabled/` | ✅ 代码完成，待建 VM 启用 |
| 魔搭创空间 | `modelscope/` + `scripts/deploy-modelscope.sh` + `.env.modelscope.example` | `workflows/deploy-server-modelscope.yml` | ✅ 当前启用 |

### 本地 Docker 运行

```bash
cd server
cp .env.example .env   # 填写 JWT_SECRET / WX_APPID / WX_SECRET
docker compose up -d
# 访问 http://localhost:8000/docs
```

### 魔搭创空间（当前启用）

```bash
cd server
cp .env.modelscope.example .env.modelscope
# 编辑填入 MODEL_SCOPE_TOKEN / MODEL_SCOPE_USERNAME / MODEL_SCOPE_STUDIO_NAME 等
bash scripts/deploy-modelscope.sh
```

> 微信小程序要求 `request` 合法域名须为**已备案 HTTPS 域名**，托管平台的默认域名（`.hf.space` / `.ms.show`）无法备案，需自备域名 Nginx 反代。详见各方案文档（`docs/plans/63/64/65-*`）。
