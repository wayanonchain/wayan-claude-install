"""Speech-to-text via Groq's Whisper transcription endpoint.

Groq exposes an OpenAI-compatible audio transcription API. Telegram voice notes
are OGG/Opus, which Whisper accepts directly, so no ffmpeg conversion is needed.
"""
from __future__ import annotations

import logging
import os

import requests

from .config import Config

log = logging.getLogger("groq")

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Extensions Groq accepts. Note: Telegram voice notes arrive as ".oga", which is
# NOT in this set even though the bytes are OGG/Opus — so it must be normalized.
ACCEPTED_EXTS = {
    "flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "opus", "wav", "webm",
}
EXT_MIME = {
    "ogg": "audio/ogg", "opus": "audio/ogg", "oga": "audio/ogg",
    "mp3": "audio/mpeg", "mpga": "audio/mpeg", "mpeg": "audio/mpeg",
    "m4a": "audio/mp4", "mp4": "audio/mp4",
    "wav": "audio/wav", "webm": "audio/webm", "flac": "audio/flac",
}


class TranscriptionError(Exception):
    """Raised when transcription cannot be produced."""


def _normalize_upload(filename: str) -> tuple[str, str]:
    """Return (groq_safe_filename, content_type).

    Telegram voice notes are OGG/Opus but come named ".oga" (or with no usable
    extension), which Groq rejects. Anything whose extension Groq does not accept
    is presented as 'voice.ogg' with an audio/ogg content type.
    """
    base = os.path.basename(filename or "").strip()
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    if ext in ACCEPTED_EXTS:
        return base, EXT_MIME.get(ext, "application/octet-stream")
    return "voice.ogg", "audio/ogg"


def transcribe(audio_bytes: bytes, filename: str, cfg: Config) -> str:
    if not cfg.groq_api_key:
        raise TranscriptionError("GROQ_API_KEY is not set")
    if not audio_bytes:
        raise TranscriptionError("empty audio")

    upload_name, content_type = _normalize_upload(filename)
    log.info("transcribing %s -> %s (%s, %d bytes) via Groq model=%s",
             filename, upload_name, content_type, len(audio_bytes), cfg.groq_model)
    try:
        resp = requests.post(
            GROQ_TRANSCRIBE_URL,
            headers={"Authorization": f"Bearer {cfg.groq_api_key}"},
            files={"file": (upload_name, audio_bytes, content_type)},
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
