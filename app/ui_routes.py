from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.config import get_settings
from app.state import _events, wait_for_events

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

router = APIRouter()

# Non-secret fields the UI is allowed to read/modify. Secrets stay in .env only.
CONFIG_FIELDS = {
    "persona_prompt": str,
    "trigger_words": list,
    "tts_provider": str,
    "tts_lang": str,
    "llm_provider": str,
    "openai_model": str,
    "openrouter_model": str,
}


def _public_state() -> dict:
    settings = get_settings()
    return {
        "persona_prompt": settings.persona_prompt,
        "trigger_words": settings.trigger_words,
        "tts_provider": settings.tts_provider,
        "tts_lang": settings.tts_lang,
        "llm_provider": settings.llm_provider,
        "openai_model": settings.openai_model,
        "openrouter_model": settings.openrouter_model,
    }


def _serialize_env_value(key: str, value) -> str:
    if key == "trigger_words":
        items = value if isinstance(value, list) else [value]
        import json as _json

        return _json.dumps([str(i).strip() for i in items], ensure_ascii=False)
    return str(value)


def _rewrite_env(updates: dict) -> None:
    """Update only the allowed non-secret keys in .env, preserving the rest."""
    lines: list[str] = []
    existing_keys: set[str] = set()
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k = stripped.split("=", 1)[0].strip().upper()
        existing_keys.add(k)

    new_lines = [line for line in lines if line.strip().startswith("#") or "=" not in line.strip()]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        k = stripped.split("=", 1)[0].strip()
        if k.upper() in CONFIG_FIELDS:
            continue  # drop; will be re-added below
        new_lines.append(line)

    for key, value in updates.items():
        new_lines.append(f"{key.upper()}={_serialize_env_value(key, value)}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.get("/overlay")
async def overlay() -> FileResponse:
    return FileResponse(STATIC_DIR / "overlay.html")


@router.get("/control")
async def control() -> FileResponse:
    return FileResponse(STATIC_DIR / "control.html")


@router.get("/api/state")
async def api_state() -> dict:
    return _public_state()


@router.post("/api/config")
async def api_config(request: Request) -> dict:
    body = await request.json()
    updates: dict[str, object] = {}
    for key in CONFIG_FIELDS:
        if key in body:
            updates[key] = body[key]
    if updates:
        _rewrite_env(updates)
        get_settings.cache_clear()
    return _public_state()


@router.post("/api/shutdown")
async def api_shutdown(background: BackgroundTasks) -> JSONResponse:
    background.add_task(_trigger_shutdown)
    return JSONResponse({"status": "stopping"})


async def _trigger_shutdown() -> None:
    await asyncio.sleep(0.2)
    os.kill(os.getpid(), 15)  # SIGTERM (Windows: terminates process)


async def _event_stream():
    yield "retry: 3000\n\n"
    sent = 0
    for event in list(_events):
        yield f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"
        sent += 1
    while True:
        try:
            await wait_for_events()
        except asyncio.CancelledError:
            break
        events = list(_events)
        if len(events) <= sent:
            continue
        for event in events[sent:]:
            yield f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"
        sent = len(events)


@router.get("/api/events")
async def api_events() -> StreamingResponse:
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
