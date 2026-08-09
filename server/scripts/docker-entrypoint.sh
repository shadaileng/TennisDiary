#!/bin/bash
set -e

# ============================================================
# Tennis Diary Server - Docker Entrypoint
# 启动时自动执行数据库迁移，然后启动 uvicorn
# HF Space 固定监听 $PORT（默认 7860），自有服务器可自定义
# ============================================================

echo "🚀 Tennis Diary Server starting..."
echo "   DATA_DIR:  ${DATA_DIR:-/app/data}"
echo "   PORT:      ${PORT:-7860}"
echo "   LOG_LEVEL: ${LOG_LEVEL:-info}"

# ① 执行 Alembic 数据库迁移（确保 schema 最新）
echo "📦 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete."

# ② 启动 uvicorn
#    --workers 1（SQLite 不支持多进程并发写入，必须单 worker）
#    --loop uvloop（性能优化）
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-7860}" \
    --log-level "${LOG_LEVEL:-info}" \
    --workers 1
