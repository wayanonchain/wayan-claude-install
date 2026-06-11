"""Configuration loaded from the agent's environment (its /etc/wayan-*.env file).

Each agent (Jupiter, Uran) gets its own env file, so the same code runs both
with fully separate configuration: token, workspace, permissions, allowlist.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    agent: str
    token: str
    workspace: str
    claude_bin: str
    claude_timeout: int
    claude_permission_mode: str
    claude_continue: bool
    poll_timeout: int
    allowed_chat_ids: frozenset[int]
    log_level: str
    # Voice input (Groq Whisper). Output/TTS is intentionally not implemented yet.
    groq_api_key: str
    groq_model: str
    voice_enabled: bool
    voice_input: bool
    voice_output: bool
    voice_timeout: int
    # File attachments (documents / photos) downloaded into the workspace.
    files_enabled: bool
    file_max_mb: int
    # Minimal-storage policy: heavy uploads are temporary; knowledge is Markdown.
    file_keep_original: bool
    file_retention_hours: int
    transcripts_enabled: bool
    transcripts_dir: str
    uploads_tmp_dir: str
    # Upload-size safety: per-type static limits + disk availability + confirm flow.
    video_max_mb: int
    audio_max_mb: int
    document_max_mb: int
    image_max_mb: int
    large_file_confirm_mb: int
    disk_min_free_mb: int
    disk_required_multiplier: int
    upload_confirmation_timeout_min: int
    # Large-file link ingestion (URLs instead of Telegram uploads).
    link_ingest_enabled: bool
    direct_url_download_enabled: bool
    ytdlp_enabled: bool
    max_redirects: int
    block_private_urls: bool
    # Visual video analysis: ffmpeg keyframes + Claude vision. Off by default;
    # when off (or ffmpeg is missing) videos fall back to audio-only analysis.
    video_visual_analysis: bool
    video_frames: int
    video_frame_max_width: int
    video_frame_jpeg_quality: int
    video_frame_extraction_timeout_sec: int
    ffmpeg_path: str
    # Debug only: keep extracted frames after analysis instead of deleting them.
    video_frame_debug_keep: bool

    @property
    def voice_input_ready(self) -> bool:
        """Voice transcription is usable only when enabled, input on, and keyed."""
        return self.voice_enabled and self.voice_input and bool(self.groq_api_key)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def load_config() -> Config:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError("TELEGRAM_BOT_TOKEN is not set (edit the agent's env file)")

    agent = os.environ.get("WAYAN_AGENT", "wayan").strip() or "wayan"

    workspace = os.environ.get("WAYAN_WORKSPACE", "").strip()
    if not workspace:
        raise ConfigError("WAYAN_WORKSPACE is not set")
    if not os.path.isdir(workspace):
        raise ConfigError(f"WAYAN_WORKSPACE does not exist: {workspace}")

    ids_raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").replace(" ", "").strip()
    if ids_raw:
        try:
            allowed = frozenset(int(x) for x in ids_raw.split(",") if x)
        except ValueError as exc:
            raise ConfigError(
                f"TELEGRAM_ALLOWED_CHAT_IDS must be comma-separated integers, got {ids_raw!r}"
            ) from exc
    else:
        allowed = frozenset()

    return Config(
        agent=agent,
        token=token,
        workspace=workspace,
        claude_bin=os.environ.get("CLAUDE_BIN", "claude").strip() or "claude",
        # CLAUDE_TASK_TIMEOUT_SEC is the documented name; CLAUDE_TIMEOUT kept
        # as a backward-compatible fallback.
        claude_timeout=_get_int("CLAUDE_TASK_TIMEOUT_SEC",
                                _get_int("CLAUDE_TIMEOUT", 300)),
        claude_permission_mode=os.environ.get("CLAUDE_PERMISSION_MODE", "").strip(),
        claude_continue=_get_bool("CLAUDE_CONTINUE", True),
        poll_timeout=_get_int("TELEGRAM_POLL_TIMEOUT", 50),
        allowed_chat_ids=allowed,
        log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        groq_api_key=os.environ.get("GROQ_API_KEY", "").strip(),
        groq_model=os.environ.get("GROQ_MODEL", "whisper-large-v3-turbo").strip()
        or "whisper-large-v3-turbo",
        voice_enabled=_get_bool("VOICE_ENABLED", True),
        voice_input=_get_bool("VOICE_INPUT", True),
        voice_output=_get_bool("VOICE_OUTPUT", False),
        voice_timeout=_get_int("VOICE_TIMEOUT", 120),
        files_enabled=_get_bool("FILES_ENABLED", True),
        file_max_mb=_get_int("FILE_MAX_MB", 100),
        file_keep_original=_get_bool("FILE_KEEP_ORIGINAL", False),
        file_retention_hours=_get_int("FILE_RETENTION_HOURS", 24),
        transcripts_enabled=_get_bool("TRANSCRIPTS_ENABLED", True),
        transcripts_dir=os.environ.get("TRANSCRIPTS_DIR", "transcripts").strip()
        or "transcripts",
        uploads_tmp_dir=os.environ.get("UPLOADS_TMP_DIR", "uploads/tmp").strip()
        or "uploads/tmp",
        video_max_mb=_get_int("VIDEO_MAX_MB", 250),
        audio_max_mb=_get_int("AUDIO_MAX_MB", 100),
        document_max_mb=_get_int("DOCUMENT_MAX_MB", 50),
        image_max_mb=_get_int("IMAGE_MAX_MB", 25),
        large_file_confirm_mb=_get_int("LARGE_FILE_CONFIRM_MB", 25),
        disk_min_free_mb=_get_int("DISK_MIN_FREE_MB", 2048),
        disk_required_multiplier=_get_int("DISK_REQUIRED_MULTIPLIER", 2),
        upload_confirmation_timeout_min=_get_int("UPLOAD_CONFIRMATION_TIMEOUT_MIN", 15),
        link_ingest_enabled=_get_bool("LINK_INGEST_ENABLED", True),
        direct_url_download_enabled=_get_bool("DIRECT_URL_DOWNLOAD_ENABLED", True),
        ytdlp_enabled=_get_bool("YTDLP_ENABLED", False),
        max_redirects=_get_int("MAX_REDIRECTS", 5),
        block_private_urls=_get_bool("BLOCK_PRIVATE_URLS", True),
        video_visual_analysis=_get_bool("VIDEO_VISUAL_ANALYSIS", False),
        video_frames=_get_int("VIDEO_FRAMES", 5),
        video_frame_max_width=_get_int("VIDEO_FRAME_MAX_WIDTH", 768),
        video_frame_jpeg_quality=_get_int("VIDEO_FRAME_JPEG_QUALITY", 75),
        video_frame_extraction_timeout_sec=_get_int(
            "VIDEO_FRAME_EXTRACTION_TIMEOUT_SEC", 60),
        ffmpeg_path=os.environ.get("FFMPEG_PATH", "/usr/bin/ffmpeg").strip()
        or "/usr/bin/ffmpeg",
        video_frame_debug_keep=_get_bool("VIDEO_FRAME_DEBUG_KEEP", False),
    )
