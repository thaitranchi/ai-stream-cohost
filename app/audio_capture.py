"""Real-time audio capture from microphone, streaming frames to Rust engine."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import Callable

import numpy as np

logger = logging.getLogger("cohost.capture")

_DEFAULT_SAMPLE_RATE = 16000
_DEFAULT_CHANNELS = 1
_DEFAULT_BLOCK_MS = 30  # 30ms frames
_DTYPE = "int16"


class AudioCapture:
    """Captures audio from the default input device and streams frames via a callback.

    Usage:
        capture = AudioCapture(on_frame=my_callback)
        capture.start()
        # ...
        capture.stop()
    """

    def __init__(
        self,
        on_frame: Callable[[bytes, int], None] | None = None,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
        channels: int = _DEFAULT_CHANNELS,
        block_ms: int = _DEFAULT_BLOCK_MS,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = int(sample_rate * block_ms / 1000)
        self.on_frame = on_frame
        self._stream = None
        self._frame_queue: queue.Queue[tuple[bytes, int]] = queue.Queue(maxsize=256)
        self._running = False
        self._thread: threading.Thread | None = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            logger.warning("Audio status: %s", status)
        pcm_bytes = indata.tobytes()
        timestamp_ms = int(time_info.inputBufferAdcTime * 1000)
        try:
            self._frame_queue.put_nowait((pcm_bytes, timestamp_ms))
        except queue.Full:
            logger.warning("Frame queue full, dropping frame")

    def start(self) -> None:
        if self._running:
            return

        try:
            import sounddevice as sd
        except ImportError:
            raise RuntimeError(
                "sounddevice is required for audio capture. "
                "Install it: pip install sounddevice"
            )

        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=_DTYPE,
            blocksize=self.block_size,
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info(
            "Audio capture started: %d Hz, %d ch, %d ms blocks",
            self.sample_rate, self.channels, self.block_size * 1000 // self.sample_rate,
        )

        if self.on_frame:
            self._thread = threading.Thread(target=self._dispatch_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("Audio capture stopped")

    def _dispatch_loop(self) -> None:
        while self._running:
            try:
                pcm_bytes, timestamp_ms = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.on_frame(pcm_bytes, timestamp_ms)
            except Exception:
                logger.exception("Error in on_frame callback")

    def read_frame(self) -> tuple[bytes, int] | None:
        """Blocking read of the next captured frame. Returns (pcm_bytes, timestamp_ms)."""
        try:
            return self._frame_queue.get(timeout=0.5)
        except queue.Empty:
            return None
