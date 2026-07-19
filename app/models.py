from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    user: str = Field(..., description="Display name of the chatter")
    message: str = Field(..., description="Raw chat message text")


class BotReply(BaseModel):
    status: str = "queued"
    user: str | None = None
    triggered: bool = False
