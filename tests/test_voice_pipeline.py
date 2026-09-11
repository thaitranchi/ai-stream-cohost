import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.voice_pipeline import VoicePipeline, _SILENCE_THRESHOLD_MS, _MIN_SPEECH_MS


def _make_chunk(is_speech: bool, timestamp_ms: int, data: bytes = b"\x00\x01" * 10):
    chunk = MagicMock()
    chunk.is_speech = is_speech
    chunk.timestamp_ms = timestamp_ms
    chunk.data = data
    return chunk


class TestVadBuffering:
    def test_buffers_speech_frames(self):
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline._speech_buffer = []
        pipeline._speech_active = False
        pipeline._last_speech_ms = 0
        pipeline._processing = False

        pipeline._on_vad_result(_make_chunk(is_speech=True, timestamp_ms=100))
        pipeline._on_vad_result(_make_chunk(is_speech=True, timestamp_ms=130))

        assert len(pipeline._speech_buffer) == 2
        assert pipeline._speech_active is True

    def test_silence_after_speech_triggers_flush(self):
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline._speech_buffer = []
        pipeline._speech_active = False
        pipeline._last_speech_ms = 0
        pipeline._processing = False
        pipeline.block_ms = 30

        pipeline._on_vad_result(_make_chunk(is_speech=True, timestamp_ms=100))
        pipeline._on_vad_result(_make_chunk(is_speech=True, timestamp_ms=130))

        with patch.object(pipeline, "_flush_speech") as mock_flush:
            pipeline._on_vad_result(_make_chunk(is_speech=False, timestamp_ms=1000))
            assert pipeline._speech_active is False
            mock_flush.assert_called_once_with(1000)

    def test_short_silence_does_not_flush(self):
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline._speech_buffer = []
        pipeline._speech_active = False
        pipeline._last_speech_ms = 0
        pipeline._processing = False

        pipeline._on_vad_result(_make_chunk(is_speech=True, timestamp_ms=500))
        pipeline._on_vad_result(_make_chunk(is_speech=False, timestamp_ms=500 + _SILENCE_THRESHOLD_MS - 1))

        assert pipeline._speech_active is True
        assert len(pipeline._speech_buffer) == 1


class TestFlushSpeech:
    def test_discards_short_speech(self):
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline.block_ms = 30
        pipeline._speech_buffer = [b"\x00" * 10] * 5  # 150ms < 300ms
        pipeline._processing = False

        pipeline._flush_speech(500)

        assert len(pipeline._speech_buffer) == 0
        assert pipeline._processing is False

    def test_discards_when_already_processing(self):
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline.block_ms = 30
        pipeline._speech_buffer = [b"\x00" * 10] * 20  # 600ms
        pipeline._processing = True

        pipeline._flush_speech(1000)

        assert len(pipeline._speech_buffer) == 0

    def test_starts_processing_thread(self):
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline.block_ms = 30
        pipeline._speech_buffer = [b"\x00" * 10] * 20  # 600ms
        pipeline._processing = False

        with patch("app.voice_pipeline.threading.Thread") as mock_thread:
            mock_thread.return_value.start = MagicMock()
            pipeline._flush_speech(1000)
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()
            assert pipeline._processing is True


class TestStartStop:
    def test_start_creates_loop_and_thread(self):
        pipeline = VoicePipeline(speaker_name="Test")

        with patch.object(pipeline._processor, "start"), \
             patch.object(pipeline._capture, "start"):
            pipeline.start()
            assert pipeline._loop is not None
            assert pipeline._loop_thread is not None
            assert pipeline._loop_thread.is_alive()
            pipeline.stop()

    def test_stop_cleans_up(self):
        pipeline = VoicePipeline(speaker_name="Test")

        with patch.object(pipeline._processor, "start"), \
             patch.object(pipeline._capture, "start"), \
             patch.object(pipeline._processor, "stop"), \
             patch.object(pipeline._capture, "stop"):
            pipeline.start()
            pipeline.stop()
            assert not pipeline._loop_thread.is_alive()
