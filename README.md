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

---

## 🛠️ Tech Stack

*   **Core Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic, pydantic-settings
*   **AI Integration:** OpenAI API (`gpt-4o-mini`)
*   **Text-to-Speech:** `gTTS` (Google Text-to-Speech) / pluggable for ElevenLabs & FPT.AI
*   **Audio Controller:** Pygame Mixer
*   **Live Chat:** `google-api-python-client` (YouTube Data API v3)

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
(orchestrates the full flow), `connectors/youtube` (optional live chat poller).

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
* `TRIGGER_WORDS` — comma-separated mentions that activate the bot.
* `TTS_PROVIDER` — `gtts` (default) or `mock` (no audio, for testing).
* YouTube connector (optional): `YOUTUBE_API_KEY`, `YOUTUBE_VIDEO_ID` (or `YOUTUBE_LIVE_CHAT_ID`).

### 4. Running the Application

Start the FastAPI server:
```bash
uvicorn cohost_bot:app --reload
```
It will be available at `http://127.0.0.1:8000` (interactive docs at `/docs`).

To also pull live chat from YouTube, run the connector in a second terminal:
```bash
python -m connectors.youtube
```

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

1. Keep the backend server (and connector, if used) running.
2. Ensure your OBS Studio configuration captures **Desktop Audio**.
3. The bot's voice plays through your system's default audio output and is mixed into the broadcast.

---

## 🗺️ Roadmap

* [x] YouTube Live Chat connector (bundled).
* [ ] FPT.AI and ElevenLabs API integration for natural Vietnamese voice cloning.
* [ ] TikTok Live connection script wrapper.
* [ ] Local Web UI for real-time monitoring and on-the-fly prompt tuning.
* [ ] OBS WebSocket triggers to change scenes based on chat interactions.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
