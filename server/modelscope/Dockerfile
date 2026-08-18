# ====================
# Tennis Diary Server - Dockerfile (ModelScope 专用)
# ====================
# 说明：
#   - 本文件为魔搭创空间(ModelScope Studio)专用，针对阿里云构建环境优化：
#       1. apt 源 → mirrors.aliyun.com（阿里云）
#       2. pip / uv 索引 → https://mirrors.aliyun.com/pypi/simple/
#   - 通用部署（HF Space / OCI）请使用根目录 server/Dockerfile。
#   - 若修改本文件，请同步考虑根目录 Dockerfile 的一致性。
#
# 多阶段构建：
#   builder：安装 Python 依赖（利用 uv 缓存层加速）
#   runtime：仅包含 .venv，精简镜像体积
# ====================

# ---------- Builder 阶段 ----------
FROM python:3.10-slim AS builder

WORKDIR /app

# 安装系统依赖（Pillow 需要 libjpeg/zlib）
# 基础镜像 python:3.10-slim 已是 Debian trixie，apt 源文件为 debian.sources
# 先替换为阿里云镜像源，再安装依赖，显著加速（deb.debian.org 跨境访问极慢）
RUN set -eux; \
    APT_SRC=/etc/apt/sources.list.d/debian.sources; \
    if [ -f "$APT_SRC" ]; then \
        sed -i 's@deb.debian.org@mirrors.aliyun.com@g' "$APT_SRC"; \
    fi; \
    apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（Python 包管理器），走阿里云 PyPI 源
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ uv

# 复制依赖声明（利用 Docker 层缓存，避免每次重建都重新安装）
COPY pyproject.toml uv.lock ./

# 安装依赖到 .venv（uv 走阿里云 PyPI 源）
ENV UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/
RUN uv venv /app/.venv && \
    uv pip install --no-cache . && \
    chmod -R a+rx /app/.venv

# ---------- Runtime 阶段 ----------
FROM python:3.10-slim AS runtime

WORKDIR /app

# 复制 builder 阶段的 .venv（完整依赖树）
COPY --from=builder /app/.venv /app/.venv

# 安装运行时系统依赖（MediaPipe 需要 libxcb.so.1，Pillow 需要 libjpeg/zlib）
# builder 阶段的系统库不会自动继承到 runtime，必须重新安装
RUN set -eux; \
    APT_SRC=/etc/apt/sources.list.d/debian.sources; \
    if [ -f "$APT_SRC" ]; then \
        sed -i 's@deb.debian.org@mirrors.aliyun.com@g' "$APT_SRC"; \
    fi; \
    apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# 将 .venv 加入 PATH，使 uvicorn、alembic 等可直接执行
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 运行时环境变量默认值（可被 docker-compose 或魔搭 Secrets 覆盖）
# 魔搭创空间持久化卷固定为 /mnt/workspace，DATA_DIR 指向它以保证重启后数据不丢
ENV DATA_DIR=/mnt/workspace
ENV UPLOAD_DIR=${DATA_DIR}/uploads
ENV LOG_DIR=${DATA_DIR}/logs

# 创建运行时目录（避免权限问题）
RUN mkdir -p ${DATA_DIR} ${UPLOAD_DIR} ${LOG_DIR}

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# 姿态推理模型（随镜像打包；构建前须存在 server/models/pose_landmarker_lite.task，
# 部署脚本会先行下载。按文件 COPY，缺失时构建失败 → fail-fast）
COPY models/pose_landmarker_lite.task ./models/

# 确保入口脚本可执行（git 索引中无执行位，COPY 后需显式添加）
RUN chmod +x scripts/docker-entrypoint.sh

# 健康检查（每 30s 检查一次，5s 超时，重试 3 次）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

EXPOSE 7860

# 生产环境启动入口
CMD ["scripts/docker-entrypoint.sh"]
