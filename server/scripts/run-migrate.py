#!/usr/bin/env python
"""直接运行数据迁移脚本"""

import sys
import os
from pathlib import Path

# 确保当前工作目录是 server 目录
os.chdir(Path(__file__).resolve().parent)

# 添加上级目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

# 现在可以导入
from scripts.migrate-sqlite-to-pg import run_migrate

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_migrate(dry_run=dry_run)
