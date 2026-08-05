> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 01-B1-1 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 创建日期 | 2026-08-05 |
> | 对应计划 | [01-tennis-diary-迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md) |
> | 关联阶段 | Phase B1：FastAPI 后台脚手架 + 数据层 |

# Step B1-1：FastAPI 项目初始化与目录结构

## 一、目标

搭建可运行的 FastAPI 服务骨架，完成依赖配置、目录结构创建、包初始化。

## 二、前置条件

- Python 3.10+ 已安装
- uv 已安装（`pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh | sh`）

## 三、详细执行步骤

### 3.1 创建项目目录结构

在 `/workspace/server/` 下创建以下目录：

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口（暂时写最小骨架）
│   ├── core/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── routers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
├── data/                        # 运行时数据目录（加入 .gitignore）
│   ├── tennis_diary.db          # SQLite 数据库文件（自动生成）
│   └── uploads/                 # 上传文件存储
│       ├── videos/              # 视频文件
│       ├── frames/              # 抽帧图片
│       └── images/              # 图片文件
├── pyproject.toml                # uv 依赖管理
├── .env.example                  # 环境变量配置模板
└── .gitignore
```

### 3.2 编写 `pyproject.toml`（uv 依赖管理）

使用 `[project]` 格式声明依赖，最低版本约束：

| 包 | 约束 | 用途 |
|---|---|---|
| fastapi | >=0.115.6 | Web 框架 |
| uvicorn[standard] | >=0.34.0 | ASGI 服务器 |
| sqlalchemy | >=2.0.36 | ORM |
| pydantic | >=2.10.3 | 数据校验 |
| python-jose[cryptography] | >=3.3.0 | JWT 签发/验证 |
| python-multipart | >=0.0.18 | 文件上传支持 |
| httpx | >=0.28.1 | 异步 HTTP 客户端（code2Session 等） |
| aiofiles | >=24.1.0 | 异步文件操作 |
| Pillow | >=11.0.0 | 图片处理（后续 Phase 用） |

### 3.3 编写 `.gitignore`

忽略项：
- `.env`（环境变量，`.env.example` 模板纳入版本管理）
- `data/`（运行时数据：SQLite + 上传文件）
- `.venv/`（uv 虚拟环境）
- `uv.lock`（uv 锁文件）
- `.pytest_cache/` / `htmlcov/` / `.coverage`（测试产物）

### 3.4 编写最小 `app/main.py` 骨架

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Tennis Diary API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
```

### 3.5 验证

```bash
cd /workspace/server
uv sync                       # 安装依赖，自动创建 .venv
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000/health` 应返回 `{"status":"ok","version":"1.0.0"}`。

访问 `http://localhost:8000/docs` 应显示 Swagger UI。

## 四、产出物

| 文件 | 说明 |
|---|---|
| `server/pyproject.toml` | uv 项目配置 + 依赖清单 |
| `server/.gitignore` | Git 忽略规则 |
| `server/app/__init__.py` | 包初始化 |
| `server/app/main.py` | FastAPI 入口（最小骨架） |
| `server/app/core/__init__.py` | core 包初始化 |
| `server/app/models/__init__.py` | models 包初始化 |
| `server/app/routers/__init__.py` | routers 包初始化 |
| `server/app/services/__init__.py` | services 包初始化 |
| `server/app/schemas/__init__.py` | schemas 包初始化 |
| `server/data/` | SQLite 数据目录（空） |
| `server/uploads/` | 上传文件目录（空） |

## 五、验收标准

- [ ] `uv sync` 无报错
- [ ] `uv run uvicorn app.main:app --port 8000` 启动成功
- [ ] `GET /health` 返回 200 + `{"status":"ok"}`
- [ ] `GET /docs` Swagger 页面可访问
