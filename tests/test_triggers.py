import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.triggers import should_respond  # noqa: E402
from app.llm import _build_client  # noqa: E402


def test_trigger_exact():
    assert should_respond("@Bot why so bad?", ["@Bot"]) is True


def test_trigger_case_insensitive():
    assert should_respond("cậu vàng hello", ["Cậu Vàng"]) is True


def test_trigger_multi():
    assert should_respond("nothing here", ["@Bot", "Cậu Vàng"]) is False


def test_trigger_empty_message():
    assert should_respond("", ["@Bot"]) is False


def test_trigger_default_words(monkeypatch):
    assert should_respond("hey Cậu Vàng") is True
