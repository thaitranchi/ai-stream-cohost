from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import get_settings  # noqa: E402
from app.pipeline import process_chat  # noqa: E402

logger = logging.getLogger("cohost.youtube")

_MAX_POLL_ERRORS = 10
_BACKOFF_BASE_S = 2.0
_BACKOFF_MAX_S = 120.0

try:
    from googleapiclient.discovery import build
except ImportError as exc:  # noqa: F401
    raise SystemExit(
        "google-api-python-client is required for the YouTube connector. "
        "Install it via requirements.txt."
    ) from exc


def _build_service(settings):
    auth_mode = (settings.youtube_auth_mode or "api_key").lower()

    if auth_mode == "oauth":
        return _build_oauth_service(settings)

    if not settings.youtube_api_key:
        raise SystemExit("YOUTUBE_API_KEY is required for the YouTube connector.")
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def _build_oauth_service(settings):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:  # noqa: F401
        raise SystemExit(
            "google-auth-oauthlib is required for YouTube OAuth. "
            "Install it via requirements.txt."
        ) from exc

    token_path = Path(settings.youtube_oauth_token_file)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            str(token_path), settings.youtube_oauth_scopes
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret_path = Path(settings.youtube_client_secret_file)
            if not secret_path.exists():
                raise SystemExit(
                    f"YouTube OAuth requires {secret_path}. Download an OAuth client "
                    "ID (Desktop app) from Google Cloud Console and save it there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secret_path), settings.youtube_oauth_scopes
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        logger.info("OAuth token cached at %s", token_path)

    return build("youtube", "v3", credentials=creds)


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


def _post_reply(youtube, chat_id: str, text: str) -> None:
    try:
        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {"messageText": text},
                }
            },
        ).execute()
        logger.info("Posted reply to chat: %s", text[:60])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to post reply: %s", exc)


def _poll(chat_id: str, youtube, settings) -> None:
    page_token: str | None = None
    seen: set[str] = set()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    post_replies = settings.youtube_post_replies
    consecutive_errors = 0

    while True:
        try:
            resp = (
                youtube.liveChatMessages()
                .list(liveChatId=chat_id, part="snippet,authorDetails", pageToken=page_token)
                .execute()
            )
            consecutive_errors = 0

            for item in resp.get("items", []):
                msg_id = item["id"]
                if msg_id in seen:
                    continue
                seen.add(msg_id)
                snippet = item["snippet"]
                author = item["authorDetails"]["displayName"]
                text = snippet.get("displayMessage") or snippet.get(
                    "textMessageDetails", {}
                ).get("messageText", "")
                if not text:
                    continue
                reply = loop.run_until_complete(process_chat(author, text))
                if post_replies and reply:
                    _post_reply(youtube, chat_id, reply)

            page_token = resp.get("nextPageToken")
            interval_ms = resp.get(
                "pollingIntervalMillis", int(settings.youtube_poll_seconds * 1000)
            )
            loop.run_until_complete(asyncio.sleep(interval_ms / 1000.0))

        except KeyboardInterrupt:
            logger.info("YouTube connector shutting down")
            break
        except Exception as exc:
            consecutive_errors += 1
            if consecutive_errors > _MAX_POLL_ERRORS:
                logger.error(
                    "YouTube connector failed %d times consecutively, stopping",
                    consecutive_errors,
                )
                break
            delay = min(_BACKOFF_BASE_S ** consecutive_errors, _BACKOFF_MAX_S)
            logger.warning(
                "Poll error (%d/%d): %s — retrying in %.1fs",
                consecutive_errors,
                _MAX_POLL_ERRORS,
                exc,
                delay,
            )
            loop.run_until_complete(asyncio.sleep(delay))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    settings = get_settings()
    youtube = _build_service(settings)
    chat_id = _resolve_live_chat_id(youtube, settings)
    auth_mode = (settings.youtube_auth_mode or "api_key").lower()
    logger.info(
        "Polling live chat %s (auth=%s, post_replies=%s)",
        chat_id,
        auth_mode,
        settings.youtube_post_replies,
    )
    _poll(chat_id, youtube, settings)


if __name__ == "__main__":
    main()
