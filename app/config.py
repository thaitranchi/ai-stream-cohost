from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core LLM
    llm_provider: str = "openai"  # "openai" or "openrouter"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    persona_prompt: str = (
        "You are the streamer's witty AI co-host. Be polite and cheerful toward "
        "viewers, but playfully sarcastic about the streamer's gaming skills."
    )

    trigger_words: list[str] = ["@Bot", "Cậu Vàng"]

    # Text-to-Speech
    tts_provider: str = "gtts"
    tts_lang: str = "vi"

    # YouTube Live Chat connector
    youtube_api_key: str = ""
    youtube_video_id: str = ""
    youtube_live_chat_id: str = ""
    youtube_poll_seconds: float = 5.0

    # YouTube auth: "api_key" (read-only) or "oauth" (user-authenticated, can post)
    youtube_auth_mode: str = "api_key"
    youtube_client_secret_file: str = "client_secret.json"
    youtube_oauth_token_file: str = "token.json"
    youtube_oauth_scopes: list[str] = [
        "https://www.googleapis.com/auth/youtube.readonly"
    ]
    # When True and OAuth has write scope, the co-host reply is posted to live chat.
    youtube_post_replies: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
