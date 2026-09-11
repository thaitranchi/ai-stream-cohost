"""Voice pipeline: mic capture -> VAD -> STT -> LLM reply -> TTS playback."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque

from app.audio_capture import AudioCapture
from app.audio_engine import AudioStreamProcessor
from app.audio import play_audio
from app.llm import generate_reply
from app.stt import transcribe
from app.state import log_event
from app.tts import get_tts_provider

logger = logging.getLogger("cohost.voice")

_SILENCE_THRESHOLD_MS = 800
_MIN_SPEECH_MS = 300


class VoicePipeline:
    """Full voice-driven co-host loop.

    Captures mic audio, streams to Rust VAD, buffers speech segments,
    transcribes via Whisper, generates LLM reply, and plays back TTS.
    """

    def __init__(self, speaker_name: str = "Host"):
        self.speaker_name = speaker_name
        self.sample_rate = 16000
        self.block_ms = 30
        self.bytes_per_block = int(self.sample_rate * self.block_ms / 1000) * 2

        self._speech_buffer: deque[bytes] = deque()
        self._speech_active = False
        self._last_speech_ms: int = 0
        self._processing = False

        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

        self._capture = AudioCapture(
            on_frame=self._on_audio_frame,
            sample_rate=self.sample_rate,
        )
        self._processor = AudioStreamProcessor(
            on_result=self._on_vad_result,
            sample_rate=self.sample_rate,
        )

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_loop, daemon=True, name="voice-async-loop"
        )
        self._loop_thread.start()
        self._processor.start()
        self._capture.start()
        logger.info("Voice pipeline started")

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop(self) -> None:
        self._capture.stop()
        self._processor.stop()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread:
            self._loop_thread.join(timeout=3)
        if self._loop and not self._loop.is_closed():
            self._loop.close()
        logger.info("Voice pipeline stopped")

    def _on_audio_frame(self, pcm_bytes: bytes, timestamp_ms: int) -> None:
        self._processor.feed(pcm_bytes, timestamp_ms)

    def _on_vad_result(self, chunk) -> None:
        now_ms = chunk.timestamp_ms

        if chunk.is_speech:
            self._speech_active = True
            self._last_speech_ms = now_ms
            self._speech_buffer.append(chunk.data)
        elif self._speech_active:
            silence_ms = now_ms - self._last_speech_ms
            if silence_ms >= _SILENCE_THRESHOLD_MS:
                self._speech_active = False
                self._flush_speech(now_ms)

    def _flush_speech(self, end_ms: int) -> None:
        if not self._speech_buffer:
            return

        total_blocks = len(self._speech_buffer)
        total_ms = total_blocks * self.block_ms

        if total_ms < _MIN_SPEECH_MS:
            logger.debug("Speech too short (%d ms), discarding", total_ms)
            self._speech_buffer.clear()
            return

        if self._processing:
            logger.debug("Already processing, discarding speech segment")
            self._speech_buffer.clear()
            return

        pcm_data = b"".join(self._speech_buffer)
        self._speech_buffer.clear()
        self._processing = True

        logger.info("Speech ended: %d ms, processing...", total_ms)
        threading.Thread(
            target=self._process_speech,
            args=(pcm_data,),
            daemon=True,
        ).start()

    def _process_speech(self, pcm_data: bytes) -> None:
        try:
            text = asyncio.run(transcribe(pcm_data, self.sample_rate))
            if not text:
                logger.info("No speech detected in audio")
                return

            logger.info("Transcribed: %s", text)
            self._submit_reply(text)
        except Exception:
            logger.exception("Error processing speech")
        finally:
            self._processing = False

    def _submit_reply(self, user_text: str) -> None:
        if self._loop is None or self._loop.is_closed():
            return

        asyncio.run_coroutine_threadsafe(
            self._generate_and_play(user_text),
            self._loop,
        )

    async def _generate_and_play(self, user_text: str) -> None:
        log_event(self.speaker_name, user_text, True)
        reply = await generate_reply(self.speaker_name, user_text)
        if not reply:
            return

        log_event(self.speaker_name, user_text, True, reply=reply)
        logger.info("Reply: %s", reply)

        audio_path = await get_tts_provider().synthesize(reply)
        if audio_path:
            await play_audio(audio_path)
