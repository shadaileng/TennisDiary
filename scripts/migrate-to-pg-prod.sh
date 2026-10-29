#!/bin/bash
# 生产环境 PostgreSQL 数据迁移脚本
# 用法：
#   1. 在 PostgreSQL 数据库上创建实例并配置连接
#   2. 运行此脚本
#   3. 验证结果

set -e

echo "============================================================"
echo "生产环境 PostgreSQL 数据迁移"
echo "============================================================"

cd "$(dirname "$0")/../server"

# 步骤 1: Alembic 基线初始化（在目标 PG 数据库上创建表结构）

echo ""
echo "--- 步骤 1: 执行 Alembic 基线初始化 ---"
echo "目标数据库: $(grep DATABASE_URL ../server/.env | head -1 | cut -d'=' -f2 | sed 's/ps:\/\/.*@.*:.*/ps:\/\/***:***@host:port\/postgres/')"

if ! grep -q "postgresql" ../server/.env; then
    echo "❌ 错误：.env 中没有配置 PostgreSQL 连接"
    exit 1
fi

# 执行 Alembic 迁移
echo "正在执行 Alembic 迁移..."
uv run alembic upgrade pg_baseline_148

# 步骤 2: 数据迁移（从 SQLite 迁移到 PG）

echo ""
echo "--- 步骤 2: 执行数据迁移 ---"

# 检查源 SQLite 数据库是否存在
if [ ! -f "data/tennis_diary.db" ]; then
    echo "❌ 错误：源 SQLite 数据库 data/tennis_diary.db 不存在"
    exit 1
fi

# 运行迁移脚本
uv run python scripts/migrate-sqlite-to-pg.py --validate-only

echo ""
echo "============================================================"
echo "✅ 迁移脚本执行完毕！"
echo "============================================================"

echo ""
echo "下一步操作:"

read -p "是否执行实际迁移？(y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "正在执行实际数据迁移..."
    uv run python scripts/migrate-sqlite-to-pg.py
    echo ""
    echo "✅ 数据迁移完成！"
else
    echo "❌ 用户取消实际迁移，仅完成了验证步骤。"
fi

echo ""
echo "请验证:"
echo "1. 数据库内容是否完整 - 检查各表记录数"
echo "2. 应用是否正常启动 - python -m uvicorn app.main:app"
echo "3. 运行核心测试 - uv run pytest -m fast"
