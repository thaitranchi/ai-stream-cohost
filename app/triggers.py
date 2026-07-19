from __future__ import annotations

from app.config import get_settings


def should_respond(message: str, triggers: list[str] | None = None) -> bool:
    if not message:
        return False
    triggers = triggers if triggers is not None else get_settings().trigger_words
    lowered = message.lower()
    return any(t.lower() in lowered for t in triggers if t)
