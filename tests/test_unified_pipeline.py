import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.unified_pipeline import UnifiedCoHost


class TestUnifiedCoHost:
    def test_init_defaults(self):
        host = UnifiedCoHost()
        assert host.enable_voice is True
        assert host.enable_youtube is True
        assert host._voice is None

    def test_init_custom(self):
        host = UnifiedCoHost(enable_voice=False, enable_youtube=False)
        assert host.enable_voice is False
        assert host.enable_youtube is False

    @patch("app.unified_pipeline.get_settings")
    @patch("app.unified_pipeline.VoicePipeline")
    def test_start_voice_when_enabled(self, mock_voice_cls, mock_settings):
        mock_settings.return_value = MagicMock(youtube_api_key="")
        mock_voice = MagicMock()
        mock_voice_cls.return_value = mock_voice

        host = UnifiedCoHost(enable_voice=True, enable_youtube=False)
        with patch.object(host, "_run_server"):
            host.start()
            mock_voice.start.assert_called_once()

    @patch("app.unified_pipeline.get_settings")
    @patch("app.unified_pipeline.VoicePipeline")
    def test_start_voice_when_disabled(self, mock_voice_cls, mock_settings):
        mock_settings.return_value = MagicMock(youtube_api_key="")

        host = UnifiedCoHost(enable_voice=False, enable_youtube=False)
        with patch.object(host, "_run_server"):
            host.start()
            mock_voice_cls.assert_not_called()

    @patch("app.unified_pipeline.get_settings")
    def test_stop_cleans_up(self, mock_settings):
        mock_settings.return_value = MagicMock(youtube_api_key="")

        host = UnifiedCoHost(enable_voice=False, enable_youtube=False)
        host._server = MagicMock()
        host.stop()
        host._server.should_exit = True

    @patch("app.unified_pipeline.get_settings")
    @patch("app.unified_pipeline.threading.Thread")
    def test_youtube_starts_when_key_present(self, mock_thread_cls, mock_settings):
        mock_settings.return_value = MagicMock(youtube_api_key="yt-key")
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        host = UnifiedCoHost(enable_voice=False, enable_youtube=True)
        with patch.object(host, "_run_server"):
            host.start()
            mock_thread.start.assert_called_once()

    @patch("app.unified_pipeline.get_settings")
    def test_youtube_skipped_when_no_key(self, mock_settings):
        mock_settings.return_value = MagicMock(youtube_api_key="")

        host = UnifiedCoHost(enable_voice=False, enable_youtube=True)
        with patch.object(host, "_run_server"):
            host.start()
            assert host._youtube_thread is None
