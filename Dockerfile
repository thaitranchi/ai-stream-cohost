FROM python:3.11-slim AS base

WORKDIR /app

# Install system deps for pygame, sounddevice (PortAudio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-2.0-0 \
    libportaudio2 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "cohost_bot:app", "--host", "0.0.0.0", "--port", "8000"]
