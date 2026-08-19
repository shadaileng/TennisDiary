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
#   runtime：仅包含 .venv + 必要系统库，精简镜像体积
#
# 镜像选择：使用 python:3.11-slim 精简镜像，手动安装 MediaPipe 所需系统库
#   - libgl1：提供 libGL.so.1（TFLite GPU 后端必需）
#   - libglib2.0-0：提供 libgthread-2.0.so.0（OpenCV 必需）
# ====================

# ---------- Builder 阶段 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

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
FROM python:3.11-slim AS runtime

WORKDIR /app

# 复制 builder 阶段的 .venv（完整依赖树）
COPY --from=builder /app/.venv /app/.venv

# 安装运行时系统依赖（MediaPipe TFLite 需要 libGL + OpenCV 需要 libglib）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
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
