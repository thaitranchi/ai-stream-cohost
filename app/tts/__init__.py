from __future__ import annotations

from app.config import get_settings
from app.tts.base import TTSProvider
from app.tts.gtts_provider import GTTSTTSProvider
from app.tts.mock_provider import MockTTSProvider


def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    name = settings.tts_provider.lower()
    if name == "mock":
        return MockTTSProvider()
    if name == "gtts":
        return GTTSTTSProvider()
    raise ValueError(f"Unknown TTS provider: {settings.tts_provider}")


__all__ = [
    "TTSProvider",
    "GTTSTTSProvider",
    "MockTTSProvider",
    "get_tts_provider",
]
