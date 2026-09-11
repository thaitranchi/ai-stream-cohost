"""Run everything: Rust engine + FastAPI + voice capture + YouTube chat."""

from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("cohost.main")


def start_rust_engine() -> subprocess.Popen | None:
    logger.info("Starting Rust audio engine...")
    try:
        proc = subprocess.Popen(
            ["cargo", "run", "--release"],
            cwd="rust-engine",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3)
        if proc.poll() is not None:
            logger.error("Rust engine exited early")
            return None
        logger.info("Rust engine running (pid=%d)", proc.pid)
        return proc
    except FileNotFoundError:
        logger.warning("cargo not found — Rust engine disabled")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Stream Co-Host")
    parser.add_argument("--no-voice", action="store_true", help="Disable mic capture")
    parser.add_argument("--no-youtube", action="store_true", help="Disable YouTube chat")
    parser.add_argument("--no-rust", action="store_true", help="Skip Rust engine startup")
    args = parser.parse_args()

    rust_proc = None
    if not args.no_rust:
        rust_proc = start_rust_engine()

    from app.unified_pipeline import UnifiedCoHost

    cohost = UnifiedCoHost(
        enable_voice=not args.no_voice,
        enable_youtube=not args.no_youtube,
    )

    def shutdown(sig, frame):
        logger.info("Shutting down...")
        cohost.stop()
        if rust_proc:
            rust_proc.terminate()
            rust_proc.wait(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        cohost.start()
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
