"""Run the full voice co-host pipeline: mic -> VAD -> STT -> LLM -> TTS playback."""

from __future__ import annotations

import logging
import signal
import sys

from app.voice_pipeline import VoicePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("cohost.run_voice")


def main() -> None:
    logger.info("Starting voice co-host pipeline...")

    pipeline = VoicePipeline(speaker_name="Host")

    def shutdown(sig, frame):
        logger.info("Shutting down...")
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    pipeline.start()

    logger.info("Voice co-host is live. Speak into your mic. Ctrl+C to stop.")
    signal.pause()


if __name__ == "__main__":
    main()
