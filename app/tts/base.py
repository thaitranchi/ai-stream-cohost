from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    async def synthesize(self, text: str) -> str:
        """Convert text to speech and return the path to an audio file."""
        ...
