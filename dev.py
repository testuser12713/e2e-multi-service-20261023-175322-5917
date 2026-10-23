"""Start the whole product for development: api, worker and web together.

Usage (from the repository root): python dev.py
Stops all three services on Ctrl+C or when one of them exits.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_PORT = os.environ.get("API_PORT", "8000")
WEB_PORT = os.environ.get("WEB_PORT", "5173")
DB_PATH = os.environ.get("JOBS_DB_PATH", str(ROOT / "data" / "jobs.db"))


def main() -> int:
    npm = shutil.which("npm") or "npm"
    api_origin = f"http://127.0.0.1:{API_PORT}"
    web_origin = f"http://127.0.0.1:{WEB_PORT},http://localhost:{WEB_PORT}"
    base = {**os.environ, "JOBS_DB_PATH": DB_PATH}
    specs = [
        (
            "api",
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", API_PORT],
            ROOT / "backend",
            {**base, "CORS_ORIGINS": web_origin},
        ),
        ("worker", [sys.executable, "-m", "worker"], ROOT, base),
        (
            "web",
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", WEB_PORT],
            ROOT / "frontend",
            {**base, "VITE_API_BASE_URL": api_origin},
        ),
    ]
    procs: list[tuple[str, subprocess.Popen]] = []
    try:
        for name, cmd, cwd, env in specs:
            print(f"[dev] starting {name}", flush=True)
            procs.append((name, subprocess.Popen(cmd, cwd=cwd, env=env)))
        print(f"[dev] open http://localhost:{WEB_PORT} (Ctrl+C stops all)", flush=True)
        while all(p.poll() is None for _, p in procs):
            time.sleep(0.5)
        for name, p in procs:
            if p.poll() is not None:
                print(f"[dev] {name} exited with code {p.returncode}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        for _, p in procs:
            if p.poll() is None:
                p.terminate()
        for _, p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
