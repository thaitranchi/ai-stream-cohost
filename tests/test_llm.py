import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.llm import _build_client  # noqa: E402


def test_openai_client_built_with_key():
    s = Settings(openai_api_key="sk-test", llm_provider="openai")
    built = _build_client(s)
    assert built is not None
    client, model = built
    assert model == "gpt-4o-mini"
    assert str(client.base_url).startswith("https://api.openai.com")


def test_openrouter_client_uses_custom_base_url():
    s = Settings(
        llm_provider="openrouter",
        openrouter_api_key="sk-or-test",
        openrouter_model="meta-llama/llama-3.3-70b-instruct:free",
    )
    built = _build_client(s)
    assert built is not None
    client, model = built
    assert "openrouter.ai/api/v1" in str(client.base_url)
    assert model == "meta-llama/llama-3.3-70b-instruct:free"


def test_no_key_returns_none():
    s = Settings(llm_provider="openai", openai_api_key="")
    assert _build_client(s) is None
