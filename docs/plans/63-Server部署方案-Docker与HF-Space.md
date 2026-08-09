> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 63 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 📋 待执行 |
> | 最后更新 | 2026-08-09 |
> | 对应功能/内容 | Server 部署方案（Docker + HF Space） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-09 | v1.0.0 | 初版 |
>
> **关联文档**：[01-Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md) · [39-Alembic 数据库迁移接入](./39-Alembic数据库迁移接入.md)

# Phase Server-1：Server 部署方案（Docker + HF Space）

## 一、目标

为 FastAPI 后台提供两种一键部署方案，支持：
- 自有服务器 Docker 部署（SQLite 持久化卷）
- Hugging Face Space 免费托管部署（CPU 档）

两者共用同一 `Dockerfile`，HF Space 通过 `Docker Runner` 运行。

## 二、产出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| Dockerfile | `server/Dockerfile` | 生产构建镜像（多阶段） |
| docker-compose.yml | `server/docker-compose.yml` | 本地一键启动（含端口映射） |
| .dockerignore | `server/.dockerignore` | 排除无关文件，加速构建 |
| Dockerfile.space | `server/Dockerfile.space` | HF Space 专用入口（继承主镜像） |
| spaces/README.md | `server/spaces/README.md` | HF Space 部署说明 |

## 三、Dockerfile 设计

### 3.1 多阶段构建

```
builder 阶段：
  - 基础镜像：python:3.10-slim
  - 安装系统依赖（libjpeg-turbo 用于 Pillow）
  - uv 安装依赖（利用 uv 缓存层）
  - COPY 源码

runtime 阶段：
  - 基础镜像：python:3.10-slim
  - 复制 builder 阶段的 .venv
  - 健康检查端点（curl 或 python 脚本）
  - 启动脚本（含 alembic upgrade + uvicorn）
```

### 3.2 关键配置

```dockerfile
# 端口
EXPOSE 7860

# 环境变量（可通过 docker-compose 或 HF Space 注入）
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV UPLOAD_DIR=/data/uploads
ENV LOG_DIR=/data/logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1
```

### 3.3 启动脚本 `server/scripts/docker-entrypoint.sh`

```bash
#!/bin/bash
set -e

# ① 执行数据库迁移
cd /app
uv run alembic upgrade head

# ② 启动 uvicorn（HF Space 固定监听 7860 端口）
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port ${PORT:-7860} \
  --log-level ${LOG_LEVEL:-info}
```

## 四、docker-compose.yml

```yaml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${SERVER_PORT:-8000}:7860"
    volumes:
      - server_data:/data
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  server_data:
    driver: local
```

### 4.1 数据持久化

- SQLite 数据库文件位于 `server_data` 卷（`/data/tennis_diary.db`）
- 上传文件（图片/视频）同样在卷内，容器重建不丢失
- 日志文件也在卷内，便于日志分析

### 4.2 本地运行

```bash
cd server
cp .env.example .env
# 编辑 .env 填入必要配置
docker compose up -d
# 访问 http://localhost:8000/docs
```

## 五、HF Space 部署

### 5.1 HF Space 要求

- 使用 **Docker Runner**（免费 CPU 档）
- 入口点监听 `7860` 端口
- 通过 `spaces/` 子目录存放 HF Space 专属文件

### 5.2 Dockerfile.space

```dockerfile
FROM tennis-diary-server:latest

# HF Space 固定端口
ENV PORT=7860

# 数据目录（HF Space 的 /src 持久化卷）
ENV DATA_DIR=/data
ENV UPLOAD_DIR=/data/uploads
ENV LOG_DIR=/data/logs

COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### 5.3 推送步骤

```bash
# ① 构建并推送镜像到 HF Container Registry
docker build -f server/Dockerfile -t public.ecr.aws/your-namespace/tennis-diary-server:latest .
docker push public.ecr.aws/your-namespace/tennis-diary-server:latest

# ② 在 Hugging Face 创建 Space
#    - Name: tennis-diary-server
#    - SDK: Docker
#    - Hardware: CPU basic (free)
#    - Container image: public.ecr.aws/your-namespace/tennis-diary-server:latest

# ③ 配置环境变量（HF Space Settings → Variables）
#    JWT_SECRET=<强随机值>
#    WX_APPID=<小程序 AppID>
#    WX_SECRET=<小程序 Secret>
#    ADMIN_DEFAULT_PASSWORD=<修改默认密码>

# ④ 配置持久化存储
#    HF Space Docker Runner 支持挂载 volume，
#    在 Space Settings → Storage 中添加 "Data" volume，
#    挂载到 /data 路径
```

### 5.4 微信小程序域名备案注意事项

HF Space 默认域名（`*.hf.space`）**无法备案**，需：
1. 自备已备案域名（如 `api.yourdomain.com`）
2. 通过 Nginx/Caddy 反代到 HF Space 实例
3. 在微信小程序后台配置 request 合法域名

```nginx
# Nginx 反代配置示例
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    location / {
        proxy_pass https://your-space-name.hf.space;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 六、数据库选择

### 6.1 SQLite（默认，适合低并发）

- 零运维，单文件数据库
- 适合个人项目、日活 < 100
- HF Space CPU 档完全满足

### 6.2 PostgreSQL（可选，适合高并发）

如需切换 PostgreSQL，修改 `.env`：

```env
DATABASE_URL=postgresql+asyncpg://user:pass@postgres-host:5432/tennis_diary
```

`docker-compose.yml` 新增数据库服务：

```yaml
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: tennis_diary
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: tennis_diary
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tennis_diary"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  server_data:
  postgres_data:
```

HF Space 不支持附加 PostgreSQL 服务，如需 PG 需部署到自有服务器或云服务商。

## 七、目录结构变更

```
server/
├── Dockerfile                    # ← 新建
├── docker-compose.yml            # ← 新建
├── .dockerignore                 # ← 新建
├── .env.example                  # ← 已存在
├── scripts/
│   └── docker-entrypoint.sh      # ← 新建
└── spaces/
    └── README.md                 # ← 新建（HF Space 部署说明）
```

## 八、部署验证清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|---------|
| 镜像构建成功 | `docker build -t tennis-diary-server .` | 无报错，镜像 ~300MB |
| 容器启动成功 | `docker compose up -d` | 容器状态 `healthy` |
| API 文档可访问 | 浏览器打开 `http://localhost:8000/docs` | Swagger UI 正常显示 |
| 健康检查通过 | `curl http://localhost:8000/health` | `{"code":0,"data":{"status":"ok","version":"1.0.0"}}` |
| 数据库迁移执行 | 查看日志 `alembic upgrade head` | 无迁移错误 |
| 微信登录流程 | POST `/api/auth/login` 传 code | 返回 JWT token |
| 数据持久化 | 重启容器后查数据库 | 数据不丢失 |

## 九、提交规范

```bash
feat(server): 添加 Docker 与 HF Space 部署方案

- 创建多阶段 Dockerfile（builder + runtime）
- 创建 docker-compose.yml（含数据卷持久化）
- 创建 .dockerignore（排除 .venv、tests 等）
- 创建 docker-entrypoint.sh（启动时自动迁移）
- 创建 spaces/README.md（HF Space 部署指南）
```
