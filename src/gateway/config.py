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
    )
