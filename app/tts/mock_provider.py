from __future__ import annotations

import os
import tempfile


class MockTTSProvider:
    """No-op provider for testing/CI: writes text to a .txt file, no audio deps."""

    async def synthesize(self, text: str) -> str:
        if not text.strip():
            return ""
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="cohost_mock_")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path
