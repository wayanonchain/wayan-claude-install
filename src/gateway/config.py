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
        claude_timeout=_get_int("CLAUDE_TIMEOUT", 300),
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
        file_max_mb=_get_int("FILE_MAX_MB", 20),
        file_keep_original=_get_bool("FILE_KEEP_ORIGINAL", False),
        file_retention_hours=_get_int("FILE_RETENTION_HOURS", 24),
        transcripts_enabled=_get_bool("TRANSCRIPTS_ENABLED", True),
        transcripts_dir=os.environ.get("TRANSCRIPTS_DIR", "transcripts").strip()
        or "transcripts",
        uploads_tmp_dir=os.environ.get("UPLOADS_TMP_DIR", "uploads/tmp").strip()
        or "uploads/tmp",
    )
