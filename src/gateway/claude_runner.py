"""Invoke Claude Code in headless mode (`claude -p`).

The prompt is the Telegram message; the working directory is the agent's
workspace, so Claude reads that workspace's CLAUDE.md / USER.md. Conversation
continuity within a running process is handled via `--continue`.
"""
from __future__ import annotations

import logging
import subprocess

from .config import Config

log = logging.getLogger("claude")


class ClaudeError(Exception):
    """Raised when the claude CLI is missing, times out, or exits non-zero."""


def run_claude(prompt: str, cfg: Config, continue_session: bool) -> str:
    cmd = [cfg.claude_bin, "-p", "--output-format", "text"]
    if cfg.claude_permission_mode:
        cmd += ["--permission-mode", cfg.claude_permission_mode]
    if continue_session:
        cmd.append("--continue")
    cmd.append(prompt)

    log.info("invoking claude (continue=%s, cwd=%s, timeout=%ss)",
             continue_session, cfg.workspace, cfg.claude_timeout)
    try:
        proc = subprocess.run(
            cmd,
            cwd=cfg.workspace,
            capture_output=True,
            text=True,
            timeout=cfg.claude_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClaudeError(f"claude timed out after {cfg.claude_timeout}s") from exc
    except FileNotFoundError as exc:
        raise ClaudeError(
            f"claude binary not found: {cfg.claude_bin!r} "
            "(is Claude Code installed and on PATH for the service user?)"
        ) from exc

    if proc.returncode != 0:
        detail = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        raise ClaudeError(f"claude exited {proc.returncode}: {detail[:500]}")

    return (proc.stdout or "").strip()
