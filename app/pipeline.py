from __future__ import annotations

import logging

from app.audio import play_audio
from app.llm import generate_reply
from app.state import log_event
from app.tts import get_tts_provider
from app.triggers import should_respond

logger = logging.getLogger("cohost")


async def process_chat(user: str, message: str) -> str | None:
    """Full pipeline: trigger -> LLM -> TTS -> audio.

    Returns the generated reply text if the message was handled, else None.
    """
    if not should_respond(message):
        return None

    reply = await generate_reply(user, message)
    if not reply:
        log_event(user, message, True, reply=None)
        return None

    log_event(user, message, True, reply=reply)

    audio_path = await get_tts_provider().synthesize(reply)
    if audio_path:
        await play_audio(audio_path)
    return reply
