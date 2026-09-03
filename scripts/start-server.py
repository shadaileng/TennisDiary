#!/usr/bin/env python3
"""start-server: 释放 8000 端口 → 前台启动 uvicorn（热重载，Ctrl+C 停止）

用法：
    python scripts/start-server.py
"""

import os
import subprocess
import sys

_PORT = 8000
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SERVER_DIR = os.path.join(_ROOT, "server")


def kill_on_port(port):
    """跨平台释放端口占用进程。"""
    if sys.platform.startswith("win"):
        try:
            r = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
        except Exception as e:
            print(f"netstat failed: {e}", file=sys.stderr)
            return
        pids = set()
        for line in r.stdout.splitlines():
            parts = line.split()
            if (
                len(parts) >= 5
                and f":{port}" in parts[1]
                and "LISTENING" in parts[-2:]
            ):
                try:
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        pids.add(pid)
                except (ValueError, IndexError):
                    pass
        for pid in sorted(pids):
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5
            )
            print(f"killed PID={pid}")
        if not pids:
            print(f"port {port} is free")
        return

    # macOS / Linux：优先 lsof，回退 fuser
    pids = set()
    try:
        r = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
    except Exception:
        pass
    if not pids:
        try:
            r = subprocess.run(
                ["fuser", f"{port}/tcp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for token in r.stdout.split():
                token = token.strip()
                if token.isdigit():
                    pids.add(int(token))
        except Exception:
            pass

    for pid in sorted(pids):
        if pid == os.getpid():
            continue
        subprocess.run(["kill", "-9", str(pid)], timeout=5)
        print(f"killed PID={pid}")
    if not pids:
        print(f"port {port} is free")


def main():
    kill_on_port(_PORT)

    # 启动命令：uv run uvicorn（沿用 server 虚拟环境），开启热重载
    cmd = [
        "uv",
        "run",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(_PORT),
        "--reload",
    ]
    print(f"starting uvicorn (--reload) on port {_PORT} (Ctrl+C to stop)")
    subprocess.call(cmd, cwd=_SERVER_DIR)


if __name__ == "__main__":
    main()
