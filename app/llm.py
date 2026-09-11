from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from app.config import get_settings

_LLM_TIMEOUT_S = 30.0
_LLM_MAX_RETRIES = 2


def _build_messages(user: str, message: str, persona: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": persona},
        {
            "role": "user",
            "content": (
                f"Viewer '{user}' said in the live chat: {message}\n"
                "Reply as the co-host. Keep it short, natural, and spoken-aloud friendly."
            ),
        },
    ]


def _build_client(settings):
    if settings.llm_provider.lower() == "openrouter":
        if not settings.openrouter_api_key:
            return None
        return AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=_LLM_TIMEOUT_S,
            max_retries=_LLM_MAX_RETRIES,
        ), settings.openrouter_model
    if not settings.openai_api_key:
        return None
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=_LLM_TIMEOUT_S,
        max_retries=_LLM_MAX_RETRIES,
    ), settings.openai_model


async def generate_reply(user: str, message: str) -> str:
    settings = get_settings()
    built = _build_client(settings)

    if built is None:
        return (
            f"Xin chào {user}, mình là co-host đây! Mà thôi, ông chủ đang chơi "
            f"tệ quá nên mình chưa kết nối được não. Hỏi lại sau nhé!"
        )

    client, model = built
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=_build_messages(user, message, settings.persona_prompt),
            max_tokens=120,
            temperature=0.9,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        await asyncio.sleep(0)
        return f"Ui, mình bị lỗi não một chút: {exc}"
