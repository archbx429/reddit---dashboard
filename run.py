"""
Entry point: start the APScheduler in a background thread and launch
the Streamlit dashboard as a subprocess. Ctrl+C shuts both down cleanly.

Usage:
    python run.py
"""

import signal
import subprocess
import sys
import time
from typing import Optional

from database import init_db
from scheduler import create_scheduler

scheduler = None
streamlit_proc: Optional[subprocess.Popen] = None


def shutdown(signum=None, frame=None) -> None:
    print("\n[Run] Shutting down ...")
    if streamlit_proc and streamlit_proc.poll() is None:
        streamlit_proc.terminate()
        try:
            streamlit_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streamlit_proc.kill()
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    print("[Run] All services stopped.")
    sys.exit(0)


def main() -> None:
    global scheduler, streamlit_proc

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Initialise database
    print("[Run] Initialising database ...")
    init_db()

    # Start background scheduler
    print("[Run] Starting scheduler (daily trigger at 10:00 Asia/Shanghai) ...")
    scheduler = create_scheduler()
    scheduler.start()

    # Launch Streamlit as a child process
    port = 8501
    print(f"[Run] Starting Streamlit at http://localhost:{port} ...")
    streamlit_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            f"--server.port={port}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    print("[Run] Services running. Press Ctrl+C to stop.\n")

    try:
        while True:
            rc = streamlit_proc.poll()
            if rc is not None:
                print(f"[Run] Streamlit exited with code {rc}")
                break
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
