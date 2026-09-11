"""gRPC client for the Rust audio engine with retries and reconnect."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Callable, Iterator

import grpc

from app.proto import audio_stream_pb2 as pb
from app.proto import audio_stream_pb2_grpc as grpc_pb

logger = logging.getLogger("cohost.audio_engine")

_GRPC_HOST = os.environ.get("RUST_ENGINE_HOST", "127.0.0.1")
_GRPC_PORT = os.environ.get("RUST_ENGINE_PORT", "50051")
_GRPC_TARGET = f"{_GRPC_HOST}:{_GRPC_PORT}"
_GRPC_TIMEOUT_S = 5.0
_MAX_RETRIES = 3
_RETRY_BACKOFF_S = 1.0
_STREAM_RECONNECT_DELAY_S = 2.0
_MAX_STREAM_RECONNECTS = 50

_channel: grpc.Channel | None = None
_stub: grpc_pb.AudioProcessorStub | None = None
_stub_lock = threading.Lock()


def _create_channel() -> grpc.Channel:
    return grpc.insecure_channel(
        _GRPC_TARGET,
        options=[
            ("grpc.keepalive_time_ms", 10_000),
            ("grpc.keepalive_timeout_ms", 5_000),
            ("grpc.max_reconnect_attempts", 5),
        ],
    )


def get_stub() -> grpc_pb.AudioProcessorStub:
    global _channel, _stub
    with _stub_lock:
        if _stub is None or _channel is None:
            _channel = _create_channel()
            _stub = grpc_pb.AudioProcessorStub(_channel)
        return _stub


def reset_stub() -> None:
    global _channel, _stub
    with _stub_lock:
        if _channel:
            try:
                _channel.close()
            except Exception:
                pass
        _channel = None
        _stub = None


def _make_frame(
    pcm_bytes: bytes,
    timestamp_ms: int = 0,
    sample_rate: int = 16000,
) -> pb.AudioFrame:
    return pb.AudioFrame(
        data=pcm_bytes,
        timestamp_ms=timestamp_ms,
        config=pb.AudioConfig(
            sample_rate=sample_rate,
            channels=1,
            encoding="pcm_i16",
        ),
    )


def detect_voice_activity(
    pcm_bytes: bytes,
    timestamp_ms: int = 0,
    sample_rate: int = 16000,
) -> pb.VadResult | None:
    """Unary RPC with retry. Returns None on permanent failure."""
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            stub = get_stub()
            return stub.DetectVoiceActivity(
                _make_frame(pcm_bytes, timestamp_ms, sample_rate),
                timeout=_GRPC_TIMEOUT_S,
            )
        except grpc.RpcError as e:
            last_err = e
            code = e.code()
            if code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                logger.warning("VAD attempt %d/%d failed (%s), retrying...", attempt + 1, _MAX_RETRIES, code)
                reset_stub()
                time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
            else:
                logger.error("VAD permanent failure: %s", e)
                return None
    logger.error("VAD exhausted %d retries: %s", _MAX_RETRIES, last_err)
    return None


def stream_audio(
    frames: Iterator[pb.AudioFrame],
) -> Iterator[pb.ProcessedChunk]:
    """Bidirectional streaming RPC."""
    stub = get_stub()
    return stub.ProcessAudio(frames, timeout=300)


class AudioStreamProcessor:
    """Streams audio frames to Rust engine with automatic reconnect.

    Call feed() to enqueue frames. Processed results arrive via on_result callback.
    """

    def __init__(
        self,
        on_result: Callable[[pb.ProcessedChunk], None] | None = None,
        sample_rate: int = 16000,
    ):
        self.sample_rate = sample_rate
        self.on_result = on_result
        self._frame_queue: queue.Queue[pb.AudioFrame] = queue.Queue(maxsize=512)
        self._running = False
        self._thread: threading.Thread | None = None
        self._reconnect_count = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._reconnect_count = 0
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()
        logger.info("Audio stream processor started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        logger.info("Audio stream processor stopped")

    def feed(self, pcm_bytes: bytes, timestamp_ms: int = 0) -> None:
        frame = _make_frame(pcm_bytes, timestamp_ms, self.sample_rate)
        try:
            self._frame_queue.put_nowait(frame)
        except queue.Full:
            logger.warning("Frame queue full, dropping frame")

    def _stream_loop(self) -> None:
        while self._running and self._reconnect_count < _MAX_STREAM_RECONNECTS:
            try:
                self._run_stream()
            except Exception:
                logger.exception("Unexpected stream error")

            if not self._running:
                break

            self._reconnect_count += 1
            delay = min(_STREAM_RECONNECT_DELAY_S * self._reconnect_count, 30.0)
            logger.warning(
                "Stream disconnected, reconnecting in %.1fs (attempt %d/%d)",
                delay, self._reconnect_count, _MAX_STREAM_RECONNECTS,
            )
            time.sleep(delay)
            reset_stub()

        if self._reconnect_count >= _MAX_STREAM_RECONNECTS:
            logger.error("Max reconnects reached, giving up")

    def _run_stream(self) -> None:
        def _frame_generator():
            while self._running:
                try:
                    frame = self._frame_queue.get(timeout=0.2)
                    yield frame
                except queue.Empty:
                    continue

        stub = get_stub()
        try:
            responses = stub.ProcessAudio(_frame_generator(), timeout=600)
            for chunk in responses:
                self._reconnect_count = 0
                if self.on_result:
                    self.on_result(chunk)
        except grpc.RpcError as e:
            logger.warning("Stream RPC error: %s", e)
