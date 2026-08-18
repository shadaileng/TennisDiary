# ====================
# Tennis Diary Server - Dockerfile
# ====================
# 多阶段构建：
#   builder：安装 Python 依赖（利用 uv 缓存层加速）
#   runtime：仅包含 .venv，精简镜像体积
# ====================

# ---------- Builder 阶段 ----------
FROM python:3.10-slim AS builder

WORKDIR /app

# 安装系统依赖（Pillow 需要 libjpeg/zlib）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（Python 包管理器）
RUN pip install --no-cache-dir uv

# 复制依赖声明（利用 Docker 层缓存，避免每次重建都重新安装）
COPY pyproject.toml uv.lock ./

# 安装依赖到 .venv
RUN uv venv /app/.venv && \
    uv pip install --no-cache . && \
    chmod -R a+rx /app/.venv

# ---------- Runtime 阶段 ----------
FROM python:3.10-slim AS runtime

WORKDIR /app

# 复制 builder 阶段的 .venv（完整依赖树）
COPY --from=builder /app/.venv /app/.venv

# 将 .venv 加入 PATH，使 uvicorn、alembic 等可直接执行
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 运行时环境变量默认值（可被 docker-compose 或 HF Space 覆盖）
# HF Space 持久化卷挂载到 /data，默认指向此处
ENV DATA_DIR=/data
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
# 可用 scripts/download-pose-model.sh 下载。按文件 COPY，缺失时构建失败 → fail-fast）
COPY models/pose_landmarker_lite.task ./models/

# 确保入口脚本可执行（git 索引中无执行位，COPY 后需显式添加）
RUN chmod +x scripts/docker-entrypoint.sh

# 健康检查（每 30s 检查一次，5s 超时，重试 3 次）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

EXPOSE 7860

# 生产环境启动入口
CMD ["scripts/docker-entrypoint.sh"]
