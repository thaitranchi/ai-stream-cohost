# AI Stream Co-Host (`ai-stream-cohost`) 🎙️🎮

An open-source, real-time AI-powered co-host assistant designed for streamers to boost viewer engagement through intelligent chat interactions, automated text-to-speech, and humorous streamer-bot dynamics.

---

## 🌟 Overview

As a streamer, managing a fast-paced live chat while staying focused on gameplay is a major challenge. **AI Stream Co-Host** solves this by acting as your virtual "co-pilot". 

The bot monitors your live feeds (TikTok, YouTube, etc.), processes questions using Large Language Models (LLMs), and responds in real-time with a custom-defined persona (e.g., highly polite to viewers, but playfully sarcastic toward the streamer's gaming skills). The text response is instantly converted to natural speech and mixed into the broadcast.

---

## ✨ Features

*   **Intelligent Chat Filtering:** Automatically parses live chat streams to detect trigger keywords (like `@Bot` or `Cậu Vàng`).
*   **Persona-Driven AI Reasoning:** Leverages OpenAI's API (`gpt-4o-mini`) with specialized prompt engineering to generate context-aware, witty, and engaging replies.
*   **Low-Latency Text-to-Speech (TTS):** Converts generated responses into speech in real-time, outputting directly to the system's default audio channel (captured seamlessly by OBS).
*   **Asynchronous Non-Blocking Architecture:** Built with FastAPI `BackgroundTasks` to ensure that API requests and audio processing run in the background, keeping your stream and gameplay completely lag-free.
*   **Modular Audio Output:** Uses lightweight Pygame mixer utilities for seamless audio playback and clean temp-file lifecycle management.

---

## 🛠️ Tech Stack

*   **Core Backend:** Python, FastAPI, Uvicorn, Pydantic
*   **AI Integration:** OpenAI API (`gpt-4o-mini`)
*   **Text-to-Speech:** `gTTS` (Google Text-to-Speech) / Extensible to ElevenLabs & FPT.AI APIs
*   **Audio Controller:** Pygame Mixer

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Installation
Clone this repository and install the required dependencies:
```bash
git clone [https://github.com/your-username/ai-stream-cohost.git](https://github.com/your-username/ai-stream-cohost.git)
cd ai-stream-cohost
pip install fastapi uvicorn openai gtts pygame pydantic

```

### 3. Environment Setup

Set up your OpenAI API key in your environment variables:

* **Linux/macOS:**
```bash
export OPENAI_API_KEY="your-openai-api-key"

```


* **Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY="your-openai-api-key"

```



### 4. Running the Application

Start the FastAPI server:

```bash
python cohost_bot.py

```

The server will start running locally at `http://127.0.0.1:8000`.

---

## 📡 API Integration

The server exposes a POST endpoint `/stream-chat` which accepts chat messages from your live stream scraper/connector.

### Request Payload:

```json
POST /stream-chat
Content-Type: application/json

{
  "user": "Gamer123",
  "message": "@Bot why is Thai playing so badly today?"
}

```

---

## 🎙️ Stream Setup (OBS Studio)

1. Keep the backend server running.
2. Ensure your OBS Studio configuration captures **Desktop Audio**.
3. The bot's voice is played through your system's default audio output device and will be mixed directly into your live broadcast.

---

## 🗺️ Roadmap

* [ ] Add FPT.AI and ElevenLabs API integration for natural Vietnamese voice cloning.
* [ ] Implement YouTube Live Chat & TikTok Live connection script wrapper out of the box.
* [ ] Build a local Web UI for real-time system monitoring and prompt tuning on-the-fly.
* [ ] Add OBS WebSocket triggers to change OBS scenes based on chat interactions (e.g., zoom in on streamer's face when bot roasts them).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.
