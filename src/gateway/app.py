"""The gateway loop: Telegram long-poll -> Claude -> Telegram reply.

Handles SIGTERM/SIGINT for graceful shutdown so `systemctl stop|restart` exits
cleanly mid-poll without dropping an in-flight reply.
"""
from __future__ import annotations

import logging
import os
import re
import signal
import time
from typing import Any, Optional

import requests

from .claude_runner import ClaudeError, run_claude
from .config import Config
from .telegram_api import TelegramClient, TelegramError
from .transcribe import TranscriptionError, transcribe

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

    def _transcribe_voice(self, chat_id: int, voice: dict[str, Any]) -> Optional[str]:
        """Download a Telegram voice/audio note and transcribe it via Groq.

        Returns the transcript, or None if voice is disabled/failed (in which
        case the user has already been told what happened).
        """
        if not (self.cfg.voice_enabled and self.cfg.voice_input):
            self.tg.send_message(chat_id, "🎤 Voice input is disabled for this agent.")
            return None
        if not self.cfg.groq_api_key:
            self.tg.send_message(
                chat_id, "🎤 Voice received, but GROQ_API_KEY is not configured.")
            return None
        file_id = voice.get("file_id")
        if not file_id:
            return None

        self.tg.send_chat_action(chat_id, "typing")
        try:
            info = self.tg.get_file(file_id)
            file_path = info.get("file_path")
            if not file_path:
                raise TranscriptionError("Telegram did not return a file_path")
            audio = self.tg.download_file(file_path)
            filename = os.path.basename(file_path) or "audio.ogg"
            transcript = transcribe(audio, filename, self.cfg)
        except (TelegramError, TranscriptionError, requests.RequestException) as exc:
            log.error("voice transcription failed: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Voice transcription failed: {exc}")
            return None

        log.info("transcribed voice from chat_id=%s (%d chars)", chat_id, len(transcript))
        # Echo what we understood so the user can confirm/correct.
        self.tg.send_message(chat_id, f"📝 {transcript}")
        return transcript

    @staticmethod
    def _largest_photo(photos: Optional[list]) -> Optional[dict[str, Any]]:
        """Telegram sends photos as a list of sizes; pick the largest (last)."""
        if not photos:
            return None
        p = photos[-1]
        return {
            "file_id": p.get("file_id"),
            "file_name": f"photo_{p.get('file_unique_id', 'img')}.jpg",
            "file_size": p.get("file_size"),
        }

    @staticmethod
    def _safe_filename(name: str) -> str:
        """basename only, restricted charset, with a timestamp prefix for uniqueness."""
        base = os.path.basename(name or "").strip() or "upload.bin"
        base = re.sub(r"[^\w.\- ]", "_", base)[:120].strip() or "upload.bin"
        return f"{int(time.time())}_{base}"

    def _handle_file(self, chat_id: int, attachment: dict[str, Any],
                     caption: str) -> Optional[str]:
        """Download a document/photo into the workspace and build a Claude prompt."""
        if not self.cfg.files_enabled:
            self.tg.send_message(chat_id, "📎 File handling is disabled for this agent.")
            return None
        file_id = attachment.get("file_id")
        if not file_id:
            return None
        size = attachment.get("file_size") or 0
        if size and size > self.cfg.file_max_mb * 1024 * 1024:
            self.tg.send_message(
                chat_id,
                f"📎 Файл слишком большой ({size // (1024 * 1024)} MB > "
                f"{self.cfg.file_max_mb} MB).")
            return None

        self.tg.send_chat_action(chat_id, "typing")
        try:
            info = self.tg.get_file(file_id)
            file_path = info.get("file_path")
            if not file_path:
                raise TelegramError("Telegram did not return a file_path")
            data = self.tg.download_file(file_path)
        except (TelegramError, requests.RequestException) as exc:
            log.error("file download failed: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Не смог скачать файл: {exc}")
            return None

        raw_name = attachment.get("file_name") or os.path.basename(file_path)
        safe = self._safe_filename(raw_name)
        uploads = os.path.join(self.cfg.workspace, "uploads")
        os.makedirs(uploads, exist_ok=True)
        dest = os.path.join(uploads, safe)
        with open(dest, "wb") as fh:
            fh.write(data)
        log.info("saved upload from chat_id=%s -> %s (%d bytes)", chat_id, dest, len(data))

        self.tg.send_message(chat_id, f"📎 Файл получен: {safe}")
        task = caption or "Пользователь прислал файл. Изучи его и помоги по нему."
        return f"{task}\n\nФайл сохранён локально: {dest}"

    def _handle_message(self, msg: dict[str, Any]) -> None:
        chat_id = msg.get("chat", {}).get("id")
        if chat_id is None:
            return
        if not self._allowed(chat_id):
            log.warning("ignoring message from unauthorized chat_id=%s", chat_id)
            return

        text = (msg.get("text") or "").strip()
        caption = (msg.get("caption") or "").strip()

        # File attachment (document or photo) takes priority; caption is the task.
        attachment = msg.get("document") or self._largest_photo(msg.get("photo"))
        if attachment:
            text = self._handle_file(chat_id, attachment, caption) or ""
        elif not text:
            # Voice path: no text and a voice/audio attachment.
            voice = msg.get("voice") or msg.get("audio")
            if voice:
                text = self._transcribe_voice(chat_id, voice) or ""

        if not text:
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
        reply = reply or "(no output)"
        self.tg.send_message(chat_id, reply)
        log.info("reply sent to chat_id=%s (%d chars)", chat_id, len(reply))

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
