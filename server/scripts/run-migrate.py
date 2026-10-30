"""直接运行数据迁移脚本"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    cmd = [sys.executable, "scripts/migrate_sqlite_to_pg.py"] + sys.argv[1:]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
