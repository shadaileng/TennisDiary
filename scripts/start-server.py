#!/usr/bin/env python3
"""start-server: 杀端口 8000 → 前台启动 uvicorn（Ctrl+C 停止）

用法：
    python scripts/start-server.py
"""

import os
import subprocess
import sys
import time

PORT = 8000
SERVER_DIR = os.path.dirname(os.path.abspath(__file__)) + "/server"
UVICORN = SERVER_DIR + "/.venv/Scripts/uvicorn.exe"
LOG_FILE = SERVER_DIR + "/data/logs/start-server.log"


def kill_on_port(port):
    try:
        r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
    except Exception as e:
        print(f"netstat failed: {e}", file=sys.stderr)
        return
    pids = set()
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in parts[-2:]:
            try:
                pid = int(parts[-1])
                if pid != os.getpid():
                    pids.add(pid)
            except (ValueError, IndexError):
                pass
    for pid in sorted(pids):
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
        print(f"killed PID={pid}")
    if not pids:
        print(f"port {port} is free")


def main():
    kill_on_port(PORT)
    # wait for port to free
    for _ in range(20):
        try:
            r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
            busy = any(f":{PORT}" in p and "LISTENING" in p for p in r.stdout.splitlines())
            if not busy:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        print(f"ERROR: port {PORT} still in use", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    print(f"starting uvicorn, log={LOG_FILE} (Ctrl+C to stop)")
    with open(LOG_FILE, "w", encoding="utf-8") as log_f:
        subprocess.call(
            [UVICORN, "app.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
            cwd=SERVER_DIR,
            stdout=log_f,
            stderr=subprocess.STDOUT,
        )


if __name__ == "__main__":
    main()
