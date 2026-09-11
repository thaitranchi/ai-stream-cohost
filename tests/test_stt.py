import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.stt import pcm_to_wav, transcribe


class TestPcmToWav:
    def test_header_length(self):
        pcm = b"\x00\x01" * 100
        wav = pcm_to_wav(pcm, sample_rate=16000)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        assert wav[36:40] == b"data"

    def test_data_preserved(self):
        pcm = b"\xAA\xBB\xCC\xDD"
        wav = pcm_to_wav(pcm, sample_rate=16000)
        assert wav[44:] == pcm

    def test_custom_sample_rate(self):
        wav = pcm_to_wav(b"\x00\x01", sample_rate=44100)
        import struct
        sr = struct.unpack_from("<I", wav, 24)[0]
        assert sr == 44100


class TestTranscribe:
    @pytest.mark.asyncio
    @patch("app.stt.get_settings")
    @patch("app.stt.AsyncOpenAI")
    async def test_returns_text(self, mock_openai_cls, mock_settings):
        mock_settings.return_value = MagicMock(
            openai_api_key="sk-test",
            llm_provider="openai",
            tts_lang="en",
        )
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=MagicMock(text="hello world")
        )

        result = await transcribe(b"\x00\x01" * 100)
        assert result == "hello world"

    @pytest.mark.asyncio
    @patch("app.stt.get_settings")
    async def test_returns_none_when_no_key(self, mock_settings):
        mock_settings.return_value = MagicMock(
            openai_api_key="",
            llm_provider="openai",
        )
        result = await transcribe(b"\x00\x01" * 100)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.stt.get_settings")
    @patch("app.stt.AsyncOpenAI")
    async def test_returns_none_on_empty_transcription(self, mock_openai_cls, mock_settings):
        mock_settings.return_value = MagicMock(
            openai_api_key="sk-test",
            llm_provider="openai",
            tts_lang="en",
        )
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=MagicMock(text="   ")
        )

        result = await transcribe(b"\x00\x01" * 100)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.stt.get_settings")
    @patch("app.stt.AsyncOpenAI")
    async def test_returns_none_on_exception(self, mock_openai_cls, mock_settings):
        mock_settings.return_value = MagicMock(
            openai_api_key="sk-test",
            llm_provider="openai",
            tts_lang="en",
        )
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=RuntimeError("API down")
        )

        result = await transcribe(b"\x00\x01" * 100)
        assert result is None
