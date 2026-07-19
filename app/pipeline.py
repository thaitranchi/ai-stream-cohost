from __future__ import annotations

import logging

from app.audio import play_audio
from app.llm import generate_reply
from app.tts import get_tts_provider
from app.triggers import should_respond

logger = logging.getLogger("cohost")


async def process_chat(user: str, message: str) -> bool:
    """Full pipeline: trigger -> LLM -> TTS -> audio. Returns True if handled."""
    if not should_respond(message):
        return False

    reply = await generate_reply(user, message)
    if not reply:
        return False

    audio_path = await get_tts_provider().synthesize(reply)
    if audio_path:
        await play_audio(audio_path)
    return True
