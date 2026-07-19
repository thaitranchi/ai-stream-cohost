from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from gtts import gTTS

from app.config import get_settings


class GTTSTTSProvider:
    def __init__(self, lang: str | None = None) -> None:
        settings = get_settings()
        self.lang = lang or settings.tts_lang

    async def synthesize(self, text: str) -> str:
        if not text.strip():
            return ""

        def _save() -> str:
            fd, path = tempfile.mkstemp(suffix=".mp3", prefix="cohost_")
            os.close(fd)
            gTTS(text=text, lang=self.lang).save(path)
            return path

        loop = asyncio.get_running_loop()
        path: str = await loop.run_in_executor(None, _save)
        return path
