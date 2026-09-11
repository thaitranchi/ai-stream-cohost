"""Speech-to-text via OpenAI Whisper API with retries."""

from __future__ import annotations

import io
import logging
import struct

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger("cohost.stt")

_STT_TIMEOUT_S = 30.0
_STT_MAX_RETRIES = 2


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Wrap raw PCM i16 bytes in a WAV header."""
    data_len = len(pcm_bytes)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_len,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        channels,
        sample_rate,
        sample_rate * channels * 2,
        channels * 2,
        16,
        b"data",
        data_len,
    )
    return header + pcm_bytes


async def transcribe(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    language: str | None = None,
) -> str | None:
    """Transcribe raw PCM audio using OpenAI Whisper. Returns text or None on failure."""
    settings = get_settings()
    api_key = settings.openai_api_key if settings.llm_provider == "openai" else settings.openrouter_api_key
    if not api_key:
        logger.warning("No API key configured for STT")
        return None

    base_url = settings.openrouter_base_url if settings.llm_provider == "openrouter" else None
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=_STT_TIMEOUT_S,
        max_retries=_STT_MAX_RETRIES,
    )

    wav_bytes = pcm_to_wav(pcm_bytes, sample_rate)
    audio_file = io.BytesIO(wav_bytes)
    audio_file.name = "audio.wav"

    try:
        resp = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language or settings.tts_lang,
        )
        text = resp.text.strip()
        if not text:
            return None
        logger.info("STT result: %s", text)
        return text
    except Exception:
        logger.exception("STT transcription failed")
        return None
