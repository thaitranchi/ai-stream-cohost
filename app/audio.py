from __future__ import annotations

import asyncio
import os

from app.config import get_settings

_initialized = False


def _ensure_init() -> None:
    global _initialized
    if not _initialized:
        import pygame

        pygame.mixer.init()
        _initialized = True


_AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


async def play_audio(path: str) -> None:
    """Play an audio file via Pygame mixer and clean up the temp file after."""
    if not path or not os.path.exists(path):
        return

    if os.path.splitext(path)[1].lower() not in _AUDIO_SUFFIXES:
        # Not a playable audio file (e.g. mock provider output) — just clean up.
        try:
            os.remove(path)
        except OSError:  # noqa: BLE001
            pass
        return

    from app.config import get_settings

    if get_settings().disable_audio:
        try:
            os.remove(path)
        except OSError:  # noqa: BLE001
            pass
        return

    def _play() -> None:
        _ensure_init()
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
        finally:
            try:
                pygame.mixer.music.unload()
            except Exception:  # noqa: BLE001
                pass
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:  # noqa: BLE001
                    pass

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _play)
