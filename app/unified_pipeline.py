"""Unified co-host orchestrator: runs chat API + voice pipeline + YouTube connector."""

from __future__ import annotations

import asyncio
import logging
import threading

import uvicorn

from app.config import get_settings
from app.voice_pipeline import VoicePipeline
from connectors.youtube import main as youtube_main

logger = logging.getLogger("cohost.unified")


class UnifiedCoHost:
    """Single orchestrator that starts all subsystems."""

    def __init__(self, enable_voice: bool = True, enable_youtube: bool = True):
        self.enable_voice = enable_voice
        self.enable_youtube = enable_youtube
        self._voice: VoicePipeline | None = None
        self._youtube_thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None

    def start(self) -> None:
        settings = get_settings()
        logger.info(
            "Unified Co-Host starting | model=%s tts=%s voice=%s youtube=%s",
            settings.openai_model,
            settings.tts_provider,
            self.enable_voice,
            self.enable_youtube,
        )

        if self.enable_voice:
            self._voice = VoicePipeline(speaker_name="Host")
            self._voice.start()
            logger.info("Voice pipeline started")

        if self.enable_youtube and settings.youtube_api_key:
            self._youtube_thread = threading.Thread(
                target=self._run_youtube, daemon=True
            )
            self._youtube_thread.start()
            logger.info("YouTube connector started")

        self._run_server()

    def _run_server(self) -> None:
        from cohost_bot import app

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def _run_youtube(self) -> None:
        try:
            youtube_main()
        except Exception:
            logger.exception("YouTube connector failed")

    def stop(self) -> None:
        if self._voice:
            self._voice.stop()
        if self._server:
            self._server.should_exit = True
        logger.info("Unified Co-Host stopped")
