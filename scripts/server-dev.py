#!/usr/bin/env python3
"""server-dev launcher: kill existing uvicorn on port 8000, then start fresh.

Usage: pnpm server:dev
Runs uvicorn in foreground (Ctrl+C stops it).
Log written to server/data/logs/server-dev.log
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT / "server"
VENV_UVICORN = SERVER_DIR / ".venv" / "Scripts" / "uvicorn.exe"
LOG_DIR = SERVER_DIR / "data" / "logs"
LOG_FILE = LOG_DIR / "server-dev.log"
PORT = 8000


def kill_on_port(port: int) -> None:
    """Kill processes listening on `port` via netstat + taskkill."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
        )
    except Exception as exc:
        print(f"[server-dev] netstat failed: {exc}", file=sys.stderr)
        return

    pids = set()
    for line in result.stdout.splitlines():
        # Windows netstat: Proto Local Address          Foreign Address        State           PID
        # e.g. TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       12345
        parts = line.split()
        if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in parts[-2:]:
            try:
                pid = int(parts[-1])
                if pid != os.getpid():
                    pids.add(pid)
            except (ValueError, IndexError):
                pass

    for pid in sorted(pids):
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=5,
            )
            print(f"[server-dev] killed PID={pid}")
        except Exception as exc:
            print(f"[server-dev] taskkill PID={pid} failed: {exc}", file=sys.stderr)


def wait_port_free(port: int, timeout: int = 10) -> bool:
    """Block until no process is listening on `port`."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in parts[-2:]:
                    break
            else:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    print(f"[server-dev] killing any process on port {PORT}...")
    kill_on_port(PORT)
    if not wait_port_free(PORT, timeout=10):
        print(f"[server-dev] ERROR: port {PORT} still in use", file=sys.stderr)
        return 1

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not VENV_UVICORN.exists():
        print(f"[server-dev] ERROR: uvicorn not found at {VENV_UVICORN}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    print(f"[server-dev] starting uvicorn (log={LOG_FILE})")
    with open(LOG_FILE, "w", encoding="utf-8") as log_f:
        proc = subprocess.Popen(
            [
                str(VENV_UVICORN),
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", str(PORT),
            ],
            cwd=str(SERVER_DIR),
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
        )

    print(f"[server-dev] uvicorn PID={proc.pid}, waiting...")
    return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
