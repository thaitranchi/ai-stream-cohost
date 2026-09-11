import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import grpc
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio_engine import (
    AudioStreamProcessor,
    _make_frame,
    detect_voice_activity,
    get_stub,
    reset_stub,
)
from app.proto import audio_stream_pb2 as pb


class TestMakeFrame:
    def test_creates_frame_with_defaults(self):
        frame = _make_frame(b"\x00\x01" * 100, timestamp_ms=1000)
        assert frame.timestamp_ms == 1000
        assert frame.config.sample_rate == 16000
        assert frame.config.channels == 1
        assert frame.config.encoding == "pcm_i16"

    def test_custom_sample_rate(self):
        frame = _make_frame(b"\x00\x01" * 10, sample_rate=44100)
        assert frame.config.sample_rate == 44100


class TestGetStub:
    def test_returns_same_stub(self):
        reset_stub()
        s1 = get_stub()
        s2 = get_stub()
        assert s1 is s2

    def test_reset_creates_new_stub(self):
        s1 = get_stub()
        reset_stub()
        s2 = get_stub()
        assert s1 is not s2


class TestDetectVoiceActivity:
    @patch("app.audio_engine.get_stub")
    def test_success(self, mock_get_stub):
        mock_stub = MagicMock()
        mock_stub.DetectVoiceActivity.return_value = pb.VadResult(
            is_speech=True, speech_probability=0.95
        )
        mock_get_stub.return_value = mock_stub

        result = detect_voice_activity(b"\x00\x01" * 100, timestamp_ms=500)
        assert result is not None
        assert result.is_speech is True

    @patch("app.audio_engine.get_stub")
    def test_rpc_error_returns_none(self, mock_get_stub):
        mock_stub = MagicMock()
        err = grpc.RpcError()
        err.code = lambda: grpc.StatusCode.INTERNAL
        err.details = lambda: "internal error"
        mock_stub.DetectVoiceActivity.side_effect = err
        mock_get_stub.return_value = mock_stub

        result = detect_voice_activity(b"\x00\x01" * 100)
        assert result is None

    @patch("app.audio_engine.get_stub")
    def test_retries_on_unavailable(self, mock_get_stub):
        mock_stub = MagicMock()
        err = grpc.RpcError()
        err.code = lambda: grpc.StatusCode.UNAVAILABLE
        err.details = lambda: "unavailable"
        mock_stub.DetectVoiceActivity.side_effect = [
            err,
            pb.VadResult(is_speech=False),
        ]
        mock_get_stub.return_value = mock_stub

        with patch("app.audio_engine.reset_stub"):
            with patch("app.audio_engine.time.sleep"):
                result = detect_voice_activity(b"\x00\x01" * 100)
                assert result is not None
                assert mock_stub.DetectVoiceActivity.call_count == 2


class TestAudioStreamProcessor:
    def test_feed_enqueues_frame(self):
        proc = AudioStreamProcessor(on_result=None)
        proc.feed(b"\x00\x01" * 10, timestamp_ms=100)
        assert not proc._frame_queue.empty()

    def test_stop_sets_running_false(self):
        proc = AudioStreamProcessor(on_result=None)
        proc._running = True
        proc.stop()
        assert proc._running is False

    @patch("app.audio_engine.get_stub")
    def test_stream_loop_reconnects(self, mock_get_stub):
        mock_stub = MagicMock()
        err = grpc.RpcError()
        err.code = lambda: grpc.StatusCode.UNAVAILABLE
        err.details = lambda: "unavailable"
        mock_stub.ProcessAudio.side_effect = err
        mock_get_stub.return_value = mock_stub

        proc = AudioStreamProcessor(on_result=None)
        proc._running = True

        with patch("app.audio_engine._MAX_STREAM_RECONNECTS", 2), \
             patch("app.audio_engine.reset_stub"), \
             patch("app.audio_engine.time.sleep"):
            proc._stream_loop()
            assert proc._reconnect_count == 2
