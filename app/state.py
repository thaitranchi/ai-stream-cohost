from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

MAX_EVENTS = 200


@dataclass
class ChatEvent:
    ts: float
    user: str
    message: str
    triggered: bool
    reply: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_events: deque[ChatEvent] = deque(maxlen=MAX_EVENTS)
_condition = asyncio.Condition()


def log_event(
    user: str,
    message: str,
    triggered: bool,
    reply: str | None = None,
) -> None:
    """Append an event to the ring buffer and notify SSE subscribers."""
    event = ChatEvent(
        ts=time.time(),
        user=user,
        message=message,
        triggered=triggered,
        reply=reply,
    )
    _events.append(event)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    if loop.is_running():
        loop.call_soon_threadsafe(_notify)


def _notify() -> None:
    async def _wake() -> None:
        async with _condition:
            _condition.notify_all()

    try:
        asyncio.create_task(_wake())
    except RuntimeError:
        pass


def recent_events() -> list[dict[str, Any]]:
    return [e.to_dict() for e in _events]


async def wait_for_events() -> None:
    """Block until new events are available (used by the SSE stream)."""
    async with _condition:
        await _condition.wait()
