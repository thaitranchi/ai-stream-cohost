from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.models import BotReply, ChatMessage
from app.pipeline import process_chat
from app.triggers import should_respond

router = APIRouter()


@router.post("/stream-chat", response_model=BotReply, status_code=202)
async def stream_chat(payload: ChatMessage, background: BackgroundTasks) -> BotReply:
    triggered = should_respond(payload.message)
    if triggered:
        background.add_task(process_chat, payload.user, payload.message)
    return BotReply(status="queued", user=payload.user, triggered=triggered)
