"""The gateway loop: Telegram long-poll -> Claude -> Telegram reply.

Handles SIGTERM/SIGINT for graceful shutdown so `systemctl stop|restart` exits
cleanly mid-poll without dropping an in-flight reply.
"""
from __future__ import annotations

import logging
import signal
import time
from typing import Any

import requests

from .claude_runner import ClaudeError, run_claude
from .config import Config
from .telegram_api import TelegramClient, TelegramError

log = logging.getLogger("app")


class Gateway:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.tg = TelegramClient(cfg.token, cfg.poll_timeout)
        self._running = True
        self._offset = 0
        # `claude --continue` resumes the most recent session in the workspace,
        # so we only add it once the first turn of this process has succeeded.
        self._session_started = False

    # -- lifecycle -----------------------------------------------------------
    def _install_signals(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum: int, _frame: Any) -> None:
        log.info("received signal %s; shutting down gracefully", signum)
        self._running = False

    # -- message handling ----------------------------------------------------
    def _allowed(self, chat_id: int) -> bool:
        if not self.cfg.allowed_chat_ids:
            return True
        return chat_id in self.cfg.allowed_chat_ids

    def _handle_message(self, msg: dict[str, Any]) -> None:
        chat_id = msg.get("chat", {}).get("id")
        text = (msg.get("text") or "").strip()
        if chat_id is None or not text:
            return
        if not self._allowed(chat_id):
            log.warning("ignoring message from unauthorized chat_id=%s", chat_id)
            return
        if text in ("/start", "/help"):
            self.tg.send_message(
                chat_id,
                f"Wayan {self.cfg.agent} is online. "
                "Send a message and I will run it through Claude.",
            )
            return

        log.info("message from chat_id=%s (%d chars)", chat_id, len(text))
        self.tg.send_chat_action(chat_id, "typing")
        try:
            reply = run_claude(
                text, self.cfg,
                continue_session=self.cfg.claude_continue and self._session_started,
            )
            self._session_started = True
        except ClaudeError as exc:
            log.error("claude error: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Claude error: {exc}")
            return
        self.tg.send_message(chat_id, reply or "(no output)")

    # -- main loop -----------------------------------------------------------
    def run(self) -> None:
        self._install_signals()
        me = self.tg.get_me()
        log.info("connected to Telegram as @%s (agent=%s)",
                 me.get("username"), self.cfg.agent)

        while self._running:
            try:
                updates = self.tg.get_updates(self._offset)
            except (requests.RequestException, TelegramError) as exc:
                if not self._running:
                    break
                log.warning("getUpdates failed: %s; retrying in 3s", exc)
                time.sleep(3)
                continue

            for upd in updates:
                self._offset = upd["update_id"] + 1
                msg = upd.get("message")
                if msg:
                    try:
                        self._handle_message(msg)
                    except Exception:  # one bad update must not kill the loop
                        log.exception("error handling update %s",
                                      upd.get("update_id"))
                if not self._running:
                    break

        log.info("gateway stopped")
