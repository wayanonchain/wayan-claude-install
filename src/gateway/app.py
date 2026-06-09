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
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from .claude_runner import ClaudeError, run_claude
from .config import Config
from .telegram_api import TelegramClient, TelegramError
from .transcribe import TranscriptionError, transcribe

log = logging.getLogger("app")

# Deterministic file-analysis prompt: Claude is explicitly instructed to read the
# file before acting, instead of relying on it deciding to. Works for any file
# type (documents, images, and future kinds) since it only references a path.
FILE_PROMPT_TEMPLATE = (
    "Task:\n\n"
    "{task}\n\n"
    "You MUST first read and inspect the file located at:\n\n"
    "{path}\n\n"
    "Only after reading the file, complete the requested task.\n\n"
    "If the file cannot be read, explain why."
)
# Default task when the user sends a file without a caption.
DEFAULT_FILE_TASK = "Analyze the uploaded file and describe its contents."

# Output protocol: anything Claude writes into the workspace 'outbox' is delivered
# back to the user as a Telegram document. Appended so file-in -> file-out works.
OUTPUT_INSTRUCTION = (
    "\n\nIf the task requires producing any output file(s), save them to this "
    "directory:\n\n{outbox}\n\n"
    "Any files you save there will be delivered back to the user automatically."
)
OUTBOX_DIRNAME = "outbox"


class Gateway:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.tg = TelegramClient(cfg.token, cfg.poll_timeout)
        self._running = True
        self._offset = 0
        # `claude --continue` resumes the most recent session in the workspace,
        # so we only add it once the first turn of this process has succeeded.
        self._session_started = False
        # Raw upload pending post-run handling (transcript + cleanup). Single
        # message in flight at a time, so a single slot is enough.
        self._pending_upload: Optional[dict[str, Any]] = None

    # -- storage (minimal-storage policy) ------------------------------------
    def _uploads_tmp(self) -> str:
        return os.path.join(self.cfg.workspace, self.cfg.uploads_tmp_dir)

    def _transcripts_dir(self) -> str:
        return os.path.join(self.cfg.workspace, self.cfg.transcripts_dir)

    def _write_transcript(self, meta: dict[str, Any], body: str) -> Optional[str]:
        """Write a Markdown transcript (with metadata) for an uploaded file.

        Markdown is the long-term knowledge format; raw heavy files are not kept.
        """
        if not self.cfg.transcripts_enabled:
            return None
        tdir = self._transcripts_dir()
        os.makedirs(tdir, exist_ok=True)
        stem = os.path.splitext(self._safe_filename(meta.get("filename") or "file"))[0]
        dest = os.path.join(tdir, f"{stem}.md")
        lines = [
            f"# Transcript: {meta.get('filename', '(unknown)')}",
            "",
            f"- Original filename: {meta.get('filename', '')}",
            f"- File size: {meta.get('size', 0)} bytes",
            f"- Date/time: {meta.get('datetime', '')}",
            f"- Agent: {self.cfg.agent}",
            f"- Telegram message id: {meta.get('message_id', '')}",
            f"- Provider/model: {meta.get('provider', '')}",
            "",
            "---",
            "",
            (body or "").strip(),
            "",
        ]
        with open(dest, "w") as fh:
            fh.write("\n".join(lines))
        log.info("wrote transcript %s", dest)
        return dest

    def _finalize_upload(self, success: bool, reply: Optional[str]) -> None:
        """After a file-derived run: persist a Markdown transcript, then drop the
        raw heavy file unless FILE_KEEP_ORIGINAL is set."""
        pu = self._pending_upload
        self._pending_upload = None
        if not pu:
            return
        if success and reply:
            self._write_transcript(
                {**pu, "provider": "claude -p (analysis)"}, reply)
        if not self.cfg.file_keep_original:
            try:
                os.remove(pu["raw_path"])
                log.info("removed raw upload (FILE_KEEP_ORIGINAL=false): %s",
                         pu["raw_path"])
            except OSError:
                pass

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

    def _transcribe_voice(self, chat_id: int, voice: dict[str, Any],
                          message_id: Any = "") -> Optional[str]:
        """Download a Telegram voice/audio note, save it to uploads/tmp, transcribe
        it via Groq, write a Markdown transcript, then delete the raw heavy file
        (unless FILE_KEEP_ORIGINAL is set).

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
        raw_path = None
        try:
            info = self.tg.get_file(file_id)
            file_path = info.get("file_path")
            if not file_path:
                raise TranscriptionError("Telegram did not return a file_path")
            audio = self.tg.download_file(file_path)
            # Save the heavy file to uploads/tmp (temporary by policy).
            tmp = self._uploads_tmp()
            os.makedirs(tmp, exist_ok=True)
            filename = self._safe_filename(os.path.basename(file_path) or "audio.ogg")
            raw_path = os.path.join(tmp, filename)
            with open(raw_path, "wb") as fh:
                fh.write(audio)
            transcript = transcribe(audio, filename, self.cfg)
        except (TelegramError, TranscriptionError, requests.RequestException) as exc:
            log.error("voice transcription failed: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Voice transcription failed: {exc}")
            if raw_path:  # don't leave a half-processed heavy file around
                try:
                    if not self.cfg.file_keep_original:
                        os.remove(raw_path)
                except OSError:
                    pass
            return None

        log.info("transcribed voice from chat_id=%s (%d chars)", chat_id, len(transcript))
        # Long-term knowledge as Markdown.
        self._write_transcript({
            "filename": os.path.basename(file_path),
            "size": len(audio),
            "datetime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "message_id": message_id,
            "provider": f"groq:{self.cfg.groq_model}",
        }, transcript)
        # Drop the raw heavy file unless explicitly kept.
        if not self.cfg.file_keep_original:
            try:
                os.remove(raw_path)
                log.info("removed raw audio (FILE_KEEP_ORIGINAL=false): %s", raw_path)
            except OSError:
                pass

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
    def _outbox_snapshot(outbox: str) -> dict[str, float]:
        """Map of {file_path: mtime} for files currently in the outbox."""
        snap: dict[str, float] = {}
        if os.path.isdir(outbox):
            for name in os.listdir(outbox):
                p = os.path.join(outbox, name)
                if os.path.isfile(p):
                    try:
                        snap[p] = os.path.getmtime(p)
                    except OSError:
                        pass
        return snap

    def _deliver_outbox(self, chat_id: int, outbox: str,
                        before: dict[str, float]) -> None:
        """Send any files created/modified in the outbox during the last run."""
        if not os.path.isdir(outbox):
            return
        for name in sorted(os.listdir(outbox)):
            p = os.path.join(outbox, name)
            if not os.path.isfile(p):
                continue
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            if p in before and mtime <= before[p]:
                continue  # unchanged since before the run
            try:
                self.tg.send_document(chat_id, p, caption=name)
                log.info("delivered file to chat_id=%s: %s", chat_id, p)
            except (TelegramError, requests.RequestException, OSError) as exc:
                log.error("failed to deliver %s: %s", p, exc)
                self.tg.send_message(
                    chat_id, f"⚠️ Не смог отправить файл {name}: {exc}")

    @staticmethod
    def _file_prompt(task: str, abs_path: str) -> str:
        """Build the deterministic 'read-then-act' prompt for an uploaded file."""
        return FILE_PROMPT_TEMPLATE.format(
            task=(task or DEFAULT_FILE_TASK).strip(), path=abs_path)

    @staticmethod
    def _safe_filename(name: str) -> str:
        """basename only, restricted charset, with a timestamp prefix for uniqueness."""
        base = os.path.basename(name or "").strip() or "upload.bin"
        base = re.sub(r"[^\w.\- ]", "_", base)[:120].strip() or "upload.bin"
        return f"{int(time.time())}_{base}"

    def _handle_file(self, chat_id: int, attachment: dict[str, Any],
                     caption: str, message_id: Any = "") -> Optional[str]:
        """Download a document/photo into uploads/tmp and build a Claude prompt.

        The raw file is temporary: after the run, a Markdown transcript is written
        and the raw file is deleted unless FILE_KEEP_ORIGINAL is set
        (see _finalize_upload)."""
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
        uploads = self._uploads_tmp()
        os.makedirs(uploads, exist_ok=True)
        dest = os.path.join(uploads, safe)
        with open(dest, "wb") as fh:
            fh.write(data)
        log.info("saved upload from chat_id=%s -> %s (%d bytes)", chat_id, dest, len(data))

        # Remember it so _finalize_upload can transcript + clean up after the run.
        self._pending_upload = {
            "raw_path": dest,
            "filename": raw_name,
            "size": len(data),
            "datetime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "message_id": message_id,
        }

        self.tg.send_message(chat_id, f"📎 Файл получен: {safe}")
        prompt = self._file_prompt(caption, os.path.abspath(dest))
        outbox = os.path.join(self.cfg.workspace, OUTBOX_DIRNAME)
        os.makedirs(outbox, exist_ok=True)
        return prompt + OUTPUT_INSTRUCTION.format(outbox=os.path.abspath(outbox))

    def _handle_message(self, msg: dict[str, Any]) -> None:
        chat_id = msg.get("chat", {}).get("id")
        if chat_id is None:
            return
        if not self._allowed(chat_id):
            log.warning("ignoring message from unauthorized chat_id=%s", chat_id)
            return

        text = (msg.get("text") or "").strip()
        caption = (msg.get("caption") or "").strip()
        message_id = msg.get("message_id", "")
        self._pending_upload = None

        # File attachment (document or photo) takes priority; caption is the task.
        attachment = msg.get("document") or self._largest_photo(msg.get("photo"))
        if attachment:
            text = self._handle_file(chat_id, attachment, caption, message_id) or ""
        elif not text:
            # Voice path: no text and a voice/audio attachment.
            voice = msg.get("voice") or msg.get("audio")
            if voice:
                text = self._transcribe_voice(chat_id, voice, message_id) or ""

        if not text:
            self._pending_upload = None
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
        # Snapshot the outbox so we can deliver any files this run produces.
        outbox = os.path.join(self.cfg.workspace, OUTBOX_DIRNAME)
        before = self._outbox_snapshot(outbox)
        try:
            reply = run_claude(
                text, self.cfg,
                continue_session=self.cfg.claude_continue and self._session_started,
            )
            self._session_started = True
        except ClaudeError as exc:
            log.error("claude error: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Claude error: {exc}")
            self._finalize_upload(success=False, reply=None)
            return
        reply = reply or "(no output)"
        self.tg.send_message(chat_id, reply)
        log.info("reply sent to chat_id=%s (%d chars)", chat_id, len(reply))
        self._deliver_outbox(chat_id, outbox, before)
        # Persist a Markdown transcript of the analysis and drop the raw upload.
        self._finalize_upload(success=True, reply=reply)

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
