"""Speech-to-text via Groq's Whisper transcription endpoint.

Groq exposes an OpenAI-compatible audio transcription API. Telegram voice notes
are OGG/Opus, which Whisper accepts directly, so no ffmpeg conversion is needed.
"""
from __future__ import annotations

import logging

import requests

from .config import Config

log = logging.getLogger("groq")

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class TranscriptionError(Exception):
    """Raised when transcription cannot be produced."""


def transcribe(audio_bytes: bytes, filename: str, cfg: Config) -> str:
    if not cfg.groq_api_key:
        raise TranscriptionError("GROQ_API_KEY is not set")
    if not audio_bytes:
        raise TranscriptionError("empty audio")

    log.info("transcribing %s (%d bytes) via Groq model=%s",
             filename, len(audio_bytes), cfg.groq_model)
    try:
        resp = requests.post(
            GROQ_TRANSCRIBE_URL,
            headers={"Authorization": f"Bearer {cfg.groq_api_key}"},
            files={"file": (filename, audio_bytes)},
            data={"model": cfg.groq_model, "response_format": "json"},
            timeout=cfg.voice_timeout,
        )
    except requests.RequestException as exc:
        raise TranscriptionError(f"Groq request failed: {exc}") from exc

    if resp.status_code != 200:
        raise TranscriptionError(f"Groq HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        text = (resp.json().get("text") or "").strip()
    except ValueError as exc:
        raise TranscriptionError("Groq returned non-JSON response") from exc

    if not text:
        raise TranscriptionError("Groq returned an empty transcript")
    return text
