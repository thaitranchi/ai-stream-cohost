# AI Stream Co-Host (`ai-stream-cohost`) 🎙️🎮

An open-source, real-time AI-powered co-host assistant designed for streamers to boost viewer engagement through intelligent chat interactions, automated text-to-speech, and humorous streamer-bot dynamics.

---

## 🌟 Overview

As a streamer, managing a fast-paced live chat while staying focused on gameplay is a major challenge. **AI Stream Co-Host** solves this by acting as your virtual "co-pilot".

The bot monitors your live feeds (YouTube, etc.), processes questions using Large Language Models (LLMs), and responds in real-time with a custom-defined persona (e.g., highly polite to viewers, but playfully sarcastic toward the streamer's gaming skills). The text response is instantly converted to natural speech and mixed into the broadcast.

---

## ✨ Features

*   **Intelligent Chat Filtering:** Automatically parses live chat streams to detect trigger keywords (like `@Bot` or `Cậu Vàng`).
*   **Persona-Driven AI Reasoning:** Leverages OpenAI's API (`gpt-4o-mini`) with specialized prompt engineering to generate context-aware, witty, and engaging replies.
*   **Low-Latency Text-to-Speech (TTS):** Converts generated responses into speech in real-time via a pluggable TTS interface (`gTTS` default; `mock` for testing).
*   **Asynchronous Non-Blocking Architecture:** Built with FastAPI `BackgroundTasks` so API requests and audio processing run in the background, keeping your stream lag-free.
*   **Modular Audio Output:** Uses Pygame mixer for seamless audio playback and clean temp-file lifecycle management.
*   **YouTube Live Chat Connector:** Bundled poller that feeds live chat straight into the bot.
*   **Lightweight Web UI:** Dependency-free browser dashboard for live monitoring, on-the-fly persona/trigger tuning, and a display-only OBS overlay — no build step, no JS framework.
*   **One-Click Launcher:** Double-click runner (`run.bat` / `run.sh`) that starts the server and YouTube connector together and opens the control panel — no terminal required.
*   **Vietnamese-First:** TTS defaults to `vi`, persona and replies are Vietnamese-friendly out of the box.

---

## 🛠️ Tech Stack

*   **Core Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic, pydantic-settings
*   **AI Integration:** OpenAI API (`gpt-4o-mini`) or OpenRouter (OpenAI-compatible, free models supported)
*   **Text-to-Speech:** `gTTS` (Google Text-to-Speech, `vi` default) / pluggable for ElevenLabs & FPT.AI
*   **Audio Controller:** Pygame Mixer
*   **Live Chat:** `google-api-python-client` (YouTube Data API v3)
*   **Web UI:** Vanilla HTML/JS/CSS + Server-Sent Events (SSE) — **zero front-end dependencies**

---

## 🏗️ Architecture

```
Live Stream Chat (YouTube Live)
        │  connectors/youtube.py  (liveChatMessages poller)
        ▼
POST /stream-chat  ──────►  FastAPI  (cohost_bot.py / app/routes.py)
   {user, message}          • triggers.py  : keyword/mention filter (@Bot, "Cậu Vàng")
        │                   • llm.py       : OpenAI gpt-4o-mini (persona prompts)
        │                   • BackgroundTasks (non-blocking)
        ▼
   app/pipeline.py  ──────►  TTS layer (app/tts, pluggable: gTTS default)
        │
        ▼
   audio.py (Pygame Mixer) ──► System default audio ──► OBS "Desktop Audio" capture
```

Components: `triggers` (filter), `llm` (reply generation), `tts` (pluggable speech
interface — `gtts` / `mock`), `audio` (Pygame playback + temp cleanup), `pipeline`
(orchestrates the full flow), `state` (in-memory event log for the UI), `ui_routes`
(Web UI + SSE + config API), `connectors/youtube` (optional live chat poller).

### Web UI & Event Flow
```
Live chat / POST /stream-chat ──► routes.py log_event() ──► state.py ring buffer
        │                                                        │
        └──► pipeline.py (LLM → TTS → audio) ──► log_event(reply)
                                                                 │
                                           GET /api/events (SSE) │
                                                 │                │
                                          /overlay.html    /control.html
                                          (OBS source)     (operator panel)
```

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have **Python 3.11+** installed. Dependencies are pinned in `requirements.txt`.

### 2. Installation
```bash
cd ai-stream-cohost
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

### 3. Environment Setup
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
* `LLM_PROVIDER` — `openai` (default) or `openrouter`.
* `OPENAI_API_KEY` / `OPENAI_MODEL` — used when `LLM_PROVIDER=openai`.
* `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` / `OPENROUTER_BASE_URL` — used when `LLM_PROVIDER=openrouter`. OpenRouter is OpenAI-compatible; the default is the free `meta-llama/llama-3.3-70b-instruct:free` (any `:free` model id works, or `openrouter/free` to auto-route). A friendly fallback reply is used if no key is set.
* `PERSONA_PROMPT` — customize the co-host's personality.
* `TRIGGER_WORDS` — JSON array of mentions/keywords that activate the bot, e.g. `["@Bot","Cậu Vàng"]`.
* `TTS_PROVIDER` — `gtts` (default) or `mock` (no audio, for testing).
* `TTS_LANG` — language for speech synthesis (default `vi`).
* YouTube connector (optional): `YOUTUBE_API_KEY`, `YOUTUBE_VIDEO_ID` (or `YOUTUBE_LIVE_CHAT_ID`).

> **Note:** `TRIGGER_WORDS` must be a JSON array in `.env` (e.g. `TRIGGER_WORDS=["@Bot","Cậu Vàng"]`),
> not a comma-separated string — pydantic-settings parses list fields as JSON.

### 4. Running the Application

#### Option A — One-click launcher (recommended, no terminal)
Double-click `run.bat` (Windows) or run `./run.sh` (macOS/Linux). It will:
1. Create `.env` from `.env.example` on first run if missing.
2. Start the FastAPI server on `http://127.0.0.1:8000`.
3. Start the YouTube connector automatically **only if** it is configured
   (`YOUTUBE_API_KEY` set, or `YOUTUBE_AUTH_MODE=oauth` with `client_secret.json` present).
4. Open the control panel in your default browser.
Press `Ctrl+C` in the launcher window (or use the **Stop server** button in the control
panel) to terminate both processes cleanly.

#### Option B — Manual (two terminals)
Start the FastAPI server:
```bash
uvicorn cohost_bot:app --reload
```
It will be available at `http://127.0.0.1:8000` (interactive API docs at `/docs`).

To also pull live chat from YouTube, run the connector in a second terminal:
```bash
python -m connectors.youtube
```

#### YouTube OAuth (optional, to post replies)

By default the connector reads chat using an API key (`YOUTUBE_AUTH_MODE=api_key`).
To have the co-host **post its replies** back into the live chat, switch to OAuth:

1. In the [Google Cloud Console](https://console.cloud.google.com/), create an
   **OAuth 2.0 Client ID** of type **Desktop app** and download the JSON as
   `client_secret.json` (already git-ignored).
2. In `.env`, set:
   ```bash
   YOUTUBE_AUTH_MODE=oauth
   YOUTUBE_OAUTH_SCOPES=https://www.googleapis.com/auth/youtube.readonly,https://www.googleapis.com/auth/youtube.force-ssl
   YOUTUBE_POST_REPLIES=true
   ```
   (`youtube.force-ssl` is the write scope required for posting.)
3. Run `python -m connectors.youtube` once. It opens a browser for consent and
   caches credentials in `token.json` for subsequent runs.

Posting is **off by default** even with OAuth; only enable `YOUTUBE_POST_REPLIES=true`
once your persona/prompting is dialed in to avoid spamming chat.

---

## 🖥️ Web UI (Monitoring & Control)

A lightweight, dependency-free dashboard is served directly by the FastAPI app. No build
step, no JavaScript frameworks — just static HTML + Server-Sent Events.

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/control` | **Control panel** — live feed, persona/trigger/TTS/LLM tuning, test console, stop button. |
| `http://127.0.0.1:8000/overlay` | **Overlay** — display-only chat + reply feed for an OBS Browser Source. |

### Control Panel (`/control`)
* **Live feed** of all chat messages (trigger messages highlighted) and the co-host's replies.
* **Persona prompt**, **trigger words**, **TTS provider/language**, and **LLM provider/model** — all editable and saved live via `POST /api/config` (persisted to `.env`, applied immediately via settings cache refresh).
* **Test console** — type a message and the bot replies (no YouTube required) so you can audition persona changes.
* **Stop server** button — issues `POST /api/shutdown`, terminates the server (and connector via the launcher), and closes the tab.

> **Security:** API keys and OAuth tokens are **never** exposed to or accepted by the UI.
> The control panel only manages non-secret configuration. Secrets stay in `.env`.

### Overlay (`/overlay`)
A dark, full-screen auto-scrolling feed of chat + replies, plus a status bar
(model / TTS / triggers / health). Add it as an OBS **Browser Source** pointing at
`http://127.0.0.1:8000/overlay`.

### API Reference (UI)
* `GET  /api/events` — SSE stream of live + buffered chat/reply events.
* `GET  /api/state`  — current non-secret configuration snapshot.
* `POST /api/config` — update non-secret config (persona, triggers, TTS, LLM). Writes `.env`.
* `POST /api/shutdown` — graceful server shutdown (used by the Stop button).

---

## 📡 API Integration

`POST /stream-chat` accepts chat messages (from your connector or any scraper).

### Request Payload:
```json
POST /stream-chat
Content-Type: application/json

{
  "user": "Gamer123",
  "message": "@Bot why is Thai playing so badly today?"
}
```
The response is `202 Accepted` immediately:
```json
{ "status": "queued", "user": "Gamer123", "triggered": true }
```
If the message does not contain a trigger word, `triggered` is `false` and no processing occurs.

---

## 🎙️ Stream Setup (OBS Studio)

1. Launch the app with `run.bat` (or `uvicorn cohost_bot:app`).
2. Ensure your OBS Studio configuration captures **Desktop Audio**.
3. The bot's voice plays through your system's default audio output and is mixed into the broadcast.
4. (Optional) Add a **Browser Source** → `http://127.0.0.1:8000/overlay` to show the live co-host feed on stream.
5. Keep the **Control Panel** (`/control`) open in a separate, hidden browser source or normal tab to tune the bot live.

---

## 🗺️ Roadmap

* [x] YouTube Live Chat connector (bundled).
* [x] Local Web UI for real-time monitoring and on-the-fly prompt tuning.
* [x] One-click launcher (`run.bat` / `run.sh`) — no terminal required.
* [x] YouTube OAuth with reply posting.
* [ ] FPT.AI and ElevenLabs API integration for natural Vietnamese voice cloning.
* [ ] TikTok Live connection script wrapper.
* [ ] OBS WebSocket triggers to change scenes based on chat interactions.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
