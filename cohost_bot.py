from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routes import router
from app.ui_routes import router as ui_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.info(
        "AI Stream Co-Host starting | model=%s tts=%s triggers=%s",
        settings.openai_model,
        settings.tts_provider,
        settings.trigger_words,
    )
    yield


app = FastAPI(title="AI Stream Co-Host", version="0.1.0", lifespan=lifespan)
app.include_router(router)
app.include_router(ui_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
