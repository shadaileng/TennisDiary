#!/usr/bin/env python3
"""kill-server: 杀掉占用 8000 端口的进程（供手动启动 uvicorn 前使用）"""

import subprocess
import sys

PORT = 8000

try:
    result = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
    )
except Exception as exc:
    print(f"netstat failed: {exc}", file=sys.stderr)
    sys.exit(1)

pids = set()
for line in result.stdout.splitlines():
    parts = line.split()
    if len(parts) >= 5 and f":{PORT}" in parts[1] and "LISTENING" in parts[-2:]:
        try:
            pid = int(parts[-1])
            if pid != __import__("os").getpid():
                pids.add(pid)
        except (ValueError, IndexError):
            pass

if not pids:
    print(f"port {PORT} is free")
    sys.exit(0)

for pid in sorted(pids):
    r = subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        print(f"killed PID={pid}")
    else:
        print(f"kill PID={pid} failed: {r.stderr.strip()}", file=sys.stderr)
