#!/usr/bin/env python
"""生产环境数据库迁移脚本（Step 2: 基线创建 + Step 7: 数据迁移）"""

import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
SERVER_DIR = BASE_DIR / "server"
os.chdir(SERVER_DIR)

print("=" * 60)
print("生产环境 PostgreSQL 数据迁移 - 执行脚本")
print("=" * 60)

def run_cmd(cmd):
    print(f"\n$ {cmd}")
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=SERVER_DIR)
    print(proc.stdout)
    if proc.returncode != 0:
        print("❌ 命令执行失败:")
        print(proc.stderr)
        sys.exit(1)
    return proc.stdout

# 步骤 1: Alembic 基线初始化
print("\n--- 步骤 1: 执行 Alembic 基线初始化 ---")
run_cmd("uv run alembic upgrade pg_baseline_148")

# 步骤 2: 数据迁移正式运行
print("\n--- 步骤 2: 执行数据迁移 ---")
run_cmd("uv run python scripts/migrate-sqlite-to-pg.py")

print("\n" + "=" * 60)
print("✅ 生产环境数据迁移完成！")
print("=" * 60)
print("\n请验证:")
print("1. 数据库内容是否完整")
print("2. 应用是否正常启动")
print("3. 运行单元测试：cd server && uv run pytest -m fast")
print("\n如需回滚，请:")
print("1. 保留现有 PostgreSQL 数据")
print("2. 将 .env 中的 DATABASE_URL 改回 SQLite")
print("3. 使用本地 SQLite 数据库启动应用")
