from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

HOST = "127.0.0.1"
PORT = "8000"
CONTROL_URL = f"http://{HOST}:{PORT}/control"
HEALTH_URL = f"http://{HOST}:{PORT}/health"

CHILDREN: list[subprocess.Popen] = []


def _ensure_env() -> None:
    if not ENV_PATH.exists():
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_PATH)
            print(f"[run] Created .env from .env.example at {ENV_PATH}")
            print("[run] Edit .env to add your API keys, then re-run if needed.")
        else:
            print("[run] Warning: .env.example not found; continuing without .env.")


def _should_run_youtube() -> bool:
    if not ENV_PATH.exists():
        return False
    text = ENV_PATH.read_text(encoding="utf-8")
    api_key = ""
    auth_mode = "api_key"
    secret = "client_secret.json"
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip().upper(), v.strip()
        if k == "YOUTUBE_API_KEY":
            api_key = v
        elif k == "YOUTUBE_AUTH_MODE":
            auth_mode = v.lower()
        elif k == "YOUTUBE_CLIENT_SECRET_FILE":
            secret = v
    if api_key:
        return True
    if auth_mode == "oauth" and (ROOT / secret).exists():
        return True
    return False


def _start_server() -> subprocess.Popen:
    cmd = [sys.executable, "-m", "uvicorn", "cohost_bot:app",
           "--host", HOST, "--port", PORT]
    return subprocess.Popen(cmd, cwd=str(ROOT))


def _start_youtube() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "connectors.youtube"], cwd=str(ROOT)
    )


def _wait_for_server(timeout: float = 30.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def _terminate_children() -> None:
    for p in CHILDREN:
        if p.poll() is None:
            try:
                if os.name == "nt":
                    p.send_signal(signal.CTRL_C_EVENT)
                else:
                    p.terminate()
            except Exception:
                pass
    for p in CHILDREN:
        try:
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def main() -> None:
    _ensure_env()
    print("[run] Starting AI Stream Co-Host…")

    server = _start_server()
    CHILDREN.append(server)

    if _should_run_youtube():
        print("[run] YouTube connector enabled — starting.")
        CHILDREN.append(_start_youtube())
    else:
        print("[run] YouTube connector disabled (no API key / OAuth secret).")

    if _wait_for_server():
        print(f"[run] Server ready at {CONTROL_URL}")
        try:
            webbrowser.open(CONTROL_URL)
        except Exception:
            pass
    else:
        print("[run] Warning: server did not report healthy in time.")

    try:
        while True:
            if server.poll() is not None:
                print("[run] Server process exited; shutting down.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[run] Interrupted by user.")
    finally:
        _terminate_children()
        print("[run] Stopped.")


if __name__ == "__main__":
    main()
