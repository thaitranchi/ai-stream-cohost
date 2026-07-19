from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import get_settings  # noqa: E402
from app.pipeline import process_chat  # noqa: E402

try:
    from googleapiclient.discovery import build
except ImportError as exc:  # noqa: F401
    raise SystemExit(
        "google-api-python-client is required for the YouTube connector. "
        "Install it via requirements.txt."
    ) from exc


def _resolve_live_chat_id(youtube, settings) -> str:
    if settings.youtube_live_chat_id:
        return settings.youtube_live_chat_id
    if not settings.youtube_video_id:
        raise SystemExit(
            "Set YOUTUBE_VIDEO_ID or YOUTUBE_LIVE_CHAT_ID in .env to use the connector."
        )
    resp = (
        youtube.videos()
        .list(part="liveStreamingDetails", id=settings.youtube_video_id)
        .execute()
    )
    items = resp.get("items", [])
    if not items:
        raise SystemExit(f"No video found for id={settings.youtube_video_id}")
    chat_id = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
    if not chat_id:
        raise SystemExit("This video is not currently live with an active chat.")
    return chat_id


def _poll(chat_id: str, youtube, settings) -> None:
    page_token: str | None = None
    seen: set[str] = set()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        resp = (
            youtube.liveChatMessages()
            .list(liveChatId=chat_id, part="snippet,authorDetails", pageToken=page_token)
            .execute()
        )
        for item in resp.get("items", []):
            msg_id = item["id"]
            if msg_id in seen:
                continue
            seen.add(msg_id)
            snippet = item["snippet"]
            author = item["authorDetails"]["displayName"]
            text = snippet.get("displayMessage") or snippet.get("textMessageDetails", {}).get(
                "messageText", ""
            )
            if not text:
                continue
            loop.run_until_complete(process_chat(author, text))

        page_token = resp.get("nextPageToken")
        interval_ms = resp.get("pollingIntervalMillis", int(settings.youtube_poll_seconds * 1000))
        loop.run_until_complete(asyncio.sleep(interval_ms / 1000.0))


def main() -> None:
    settings = get_settings()
    if not settings.youtube_api_key:
        raise SystemExit("YOUTUBE_API_KEY is required for the YouTube connector.")
    youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
    chat_id = _resolve_live_chat_id(youtube, settings)
    print(f"[youtube] Polling live chat {chat_id} ...")
    _poll(chat_id, youtube, settings)


if __name__ == "__main__":
    main()
