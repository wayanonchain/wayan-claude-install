"""The gateway loop: Telegram long-poll -> Claude -> Telegram reply.

Handles SIGTERM/SIGINT for graceful shutdown so `systemctl stop|restart` exits
cleanly mid-poll without dropping an in-flight reply.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from . import link_ingest
from .claude_runner import ClaudeError, run_claude
from .config import Config
from .telegram_api import TelegramClient, TelegramError
from .transcribe import TranscriptionError, transcribe

log = logging.getLogger("app")

MB = 1024 * 1024
# Telegram Bot API cannot download files larger than this via getFile.
TELEGRAM_DOWNLOAD_LIMIT_MB = 20

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
        # Large uploads awaiting an explicit "PROCESS FILE" confirmation, per chat.
        self._pending_confirmations: dict[int, dict[str, Any]] = {}
        # Large links awaiting an explicit "PROCESS LINK" confirmation, per chat.
        self._pending_links: dict[int, dict[str, Any]] = {}
        # Task queue: updates are acked instantly in the receive loop and
        # processed sequentially by a single worker. Claude calls are guarded by
        # a global lock — one `claude --continue` session per workspace, so true
        # parallel execution would corrupt it.
        self._tasks: deque[dict[str, Any]] = deque()
        self._tasks_lock = threading.Lock()
        self._task_event = threading.Event()
        self._claude_lock = threading.Lock()
        self._current_task: Optional[dict[str, Any]] = None

    # -- task queue ------------------------------------------------------------
    def _enqueue(self, chat_id: int, msg: dict[str, Any]) -> int:
        """Add a task; returns its queue position (1 = next/immediate)."""
        with self._tasks_lock:
            self._tasks.append({"chat_id": chat_id, "msg": msg, "ts": time.time()})
            pos = len(self._tasks) + (1 if self._current_task else 0)
        self._task_event.set()
        return pos

    def _cmd_queue(self, chat_id: int) -> None:
        with self._tasks_lock:
            mine = sum(1 for t in self._tasks if t["chat_id"] == chat_id)
            total = len(self._tasks)
            cur = self._current_task
        lines = [f"📋 Queue: {total} pending task(s) total, {mine} from this chat."]
        if cur is None:
            lines.append("Idle — the next task starts immediately.")
        elif cur["chat_id"] == chat_id:
            lines.append("⏳ Your task is currently running.")
        else:
            lines.append("⏳ A task from another chat is currently running.")
        self.tg.send_message(chat_id, "\n".join(lines))

    def _cmd_cancel(self, chat_id: int) -> None:
        with self._tasks_lock:
            before = len(self._tasks)
            self._tasks = deque(t for t in self._tasks if t["chat_id"] != chat_id)
            removed = before - len(self._tasks)
            running = (self._current_task is not None
                       and self._current_task["chat_id"] == chat_id)
        log.info("cancel chat_id=%s removed=%d", chat_id, removed)
        note = f"🗑 Cancelled {removed} pending task(s)."
        if running:
            note += " The currently running task cannot be interrupted and will finish."
        self.tg.send_message(chat_id, note)

    def _process_next(self) -> bool:
        """Process one queued task. Returns False if the queue was empty.
        Never silent: every outcome produces a message to the chat."""
        with self._tasks_lock:
            if not self._tasks:
                return False
            task = self._tasks.popleft()
            self._current_task = task
        try:
            with self._claude_lock:
                self._handle_message(task["msg"])
        except Exception as exc:  # noqa: BLE001 — worker must survive anything
            log.exception("task failed chat_id=%s", task["chat_id"])
            try:
                self.tg.send_message(task["chat_id"], f"⚠️ Task failed: {exc}")
            except Exception:
                log.exception("could not notify chat %s of failure", task["chat_id"])
        finally:
            with self._tasks_lock:
                self._current_task = None
        return True

    def _worker_loop(self) -> None:
        log.info("task worker started")
        while self._running:
            if not self._process_next():
                self._task_event.wait(timeout=1.0)
                self._task_event.clear()
        log.info("task worker stopped")

    def _handle_update(self, msg: dict[str, Any]) -> None:
        """Fast receive-side routing: instant acks + commands; heavy work queued."""
        chat_id = msg.get("chat", {}).get("id")
        if chat_id is None:
            return
        if not self._allowed(chat_id):
            log.warning("ignoring update from unauthorized chat_id=%s", chat_id)
            return

        text = (msg.get("text") or "").strip()
        if text in ("/start", "/help"):
            self.tg.send_message(
                chat_id,
                f"Wayan {self.cfg.agent} is online. Send a message and I will run "
                "it through Claude.\nCommands: /queue — show queue, /cancel — drop "
                "your pending tasks.")
            return
        if text == "/queue":
            self._cmd_queue(chat_id)
            return
        if text == "/cancel":
            self._cmd_cancel(chat_id)
            return

        att = self._classify_attachment(msg)
        voice = msg.get("voice") or msg.get("audio")
        if not (text or att or voice):
            return  # nothing processable (sticker etc.) — same as before

        pos = self._enqueue(chat_id, msg)
        if att and att["kind"] == "video":
            self.tg.send_message(
                chat_id,
                "🎥 Video received. Checking size and processing options... "
                f"(queue position: {pos})")
        else:
            self.tg.send_message(chat_id, f"✅ Task received. Queue position: {pos}")

    # -- upload-size safety gate ---------------------------------------------
    def _free_mb(self) -> int:
        """Free space (MB) on the workspace filesystem."""
        try:
            return shutil.disk_usage(self.cfg.workspace).free // (1024 * 1024)
        except OSError:
            return 0

    def _type_limit_mb(self, kind: str) -> int:
        return {
            "video": self.cfg.video_max_mb,
            "audio": self.cfg.audio_max_mb,
            "image": self.cfg.image_max_mb,
            "document": self.cfg.document_max_mb,
        }.get(kind, self.cfg.file_max_mb)

    def _required_free_mb(self, size_mb: float) -> int:
        return int(size_mb * self.cfg.disk_required_multiplier + self.cfg.disk_min_free_mb)

    def _classify_attachment(self, msg: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Identify a single attachment, its type and size, from a message."""
        obj = msg.get("video") or msg.get("video_note")
        kind = "video" if obj else None
        if not obj:
            obj = msg.get("voice") or msg.get("audio")
            kind = "audio" if obj else None
        if not obj:
            obj = self._largest_photo(msg.get("photo"))
            kind = "image" if obj else None
        if not obj:
            doc = msg.get("document")
            if doc:
                obj = doc
                mime = doc.get("mime_type") or ""
                kind = ("video" if mime.startswith("video/")
                        else "audio" if mime.startswith("audio/")
                        else "image" if mime.startswith("image/")
                        else "document")
        if not obj:
            return None
        size = int(obj.get("file_size") or 0)
        return {
            "obj": obj,
            "kind": kind,
            "size_bytes": size,
            "size_mb": size / (1024 * 1024),
            "limit_mb": self._type_limit_mb(kind),
        }

    @staticmethod
    def _fmt_disk(mb: int) -> str:
        return f"{mb / 1024:.0f} GB" if mb >= 1024 else f"{mb} MB"

    def _gate_attachment(self, chat_id: int, att: dict[str, Any], caption: str,
                         message_id: Any) -> Optional[str]:
        """Two-step gate: static type limit, then disk availability. Returns a
        Claude prompt if a (small) file was processed immediately, else None
        (rejected, or pending PROCESS FILE confirmation)."""
        if not self.cfg.files_enabled:
            self.tg.send_message(chat_id, "📎 File handling is disabled for this agent.")
            return None
        kind, size_mb, limit = att["kind"], att["size_mb"], att["limit_mb"]
        size_i = int(round(size_mb))

        # 1) Static type limit — reject oversized BEFORE any download.
        if size_mb > limit:
            log.info("upload_rejected_size kind=%s size_mb=%.1f limit=%d chat_id=%s",
                     kind, size_mb, limit, chat_id)
            self.tg.send_message(
                chat_id,
                f"❌ File too large\n\nType: {kind}\nSize: {size_i} MB\n"
                f"Limit: {limit} MB\n\nPlease upload a smaller file or provide a link.")
            return None

        # Telegram bots cannot fetch files over ~20 MB — redirect to link ingestion.
        if size_mb > TELEGRAM_DOWNLOAD_LIMIT_MB:
            log.info("upload_rejected_size (telegram cap) kind=%s size_mb=%.1f chat_id=%s",
                     kind, size_mb, chat_id)
            self.tg.send_message(
                chat_id,
                "Telegram cannot provide large files to bots.\n"
                "Please send a direct link to the video/audio instead.\n"
                "For YouTube/Reels/TikTok, send the public link.")
            return None

        # 7) Small files (< confirm threshold) process immediately.
        if size_mb < self.cfg.large_file_confirm_mb:
            return self._process_attachment(chat_id, att, caption, message_id)

        # 2) Disk availability for large-but-allowed files.
        avail = self._free_mb()
        required = self._required_free_mb(size_mb)
        if avail < required:
            log.info("upload_rejected_disk size_mb=%.1f required=%d avail=%d chat_id=%s",
                     size_mb, required, avail, chat_id)
            self.tg.send_message(
                chat_id,
                f"❌ Not enough disk space\n\nFile size: {size_i} MB\n"
                f"Required free space: {required} MB\nAvailable free space: {avail} MB\n\n"
                "Please free disk space or send a smaller file.")
            return None

        # 3) Large but allowed: store pending and ask for confirmation.
        self._pending_confirmations[chat_id] = {
            "att": att, "caption": caption, "message_id": message_id,
            "created_at": time.time(),
        }
        est = int(round(size_mb * self.cfg.disk_required_multiplier))
        log.info("large_upload_pending kind=%s size_mb=%.1f chat_id=%s msg_id=%s",
                 kind, size_mb, chat_id, message_id)
        self.tg.send_message(
            chat_id,
            f"⚠️ Large file detected\n\nType: {kind}\nSize: {size_i} MB\n"
            f"Limit: {limit} MB\nAvailable disk: {self._fmt_disk(avail)}\n"
            f"Estimated temporary usage: up to {est} MB\n\n"
            "Reply with:\nPROCESS FILE\n\nto continue.")
        return None

    def _confirm_pending(self, chat_id: int) -> Optional[str]:
        """Handle a 'PROCESS FILE' reply: re-check disk, then download+process."""
        pend = self._pending_confirmations.pop(chat_id, None)
        if not pend:
            self.tg.send_message(chat_id, "No file is awaiting confirmation.")
            return None
        if time.time() - pend["created_at"] > self.cfg.upload_confirmation_timeout_min * 60:
            log.info("large_upload_expired chat_id=%s", chat_id)
            self.tg.send_message(
                chat_id, "⏳ Confirmation expired. Please re-send the file.")
            return None

        att = pend["att"]
        size_mb = att["size_mb"]
        avail = self._free_mb()
        required = self._required_free_mb(size_mb)
        if avail < required:  # re-check disk after confirmation
            log.info("upload_rejected_disk (recheck) size_mb=%.1f required=%d avail=%d chat_id=%s",
                     size_mb, required, avail, chat_id)
            self.tg.send_message(
                chat_id,
                f"❌ Not enough disk space\n\nFile size: {int(round(size_mb))} MB\n"
                f"Required free space: {required} MB\nAvailable free space: {avail} MB\n\n"
                "Please free disk space or send a smaller file.")
            return None

        log.info("large_upload_confirmed kind=%s size_mb=%.1f chat_id=%s",
                 att["kind"], size_mb, chat_id)
        return self._process_attachment(
            chat_id, att, pend["caption"], pend["message_id"])

    def _process_attachment(self, chat_id: int, att: dict[str, Any], caption: str,
                            message_id: Any) -> Optional[str]:
        """Download + route an approved attachment; returns a Claude prompt."""
        kind = att["kind"]
        if kind in ("audio", "video"):
            text = self._transcribe_voice(chat_id, att["obj"], message_id)
        else:  # image / document
            text = self._handle_file(chat_id, att["obj"], caption, message_id)
        if text:
            log.info("upload_processed kind=%s chat_id=%s", kind, chat_id)
        return text

    # -- link ingestion ------------------------------------------------------
    def _detect_ingest_link(self, text: str) -> Optional[dict[str, Any]]:
        """If the text contains an ingestible file/platform URL, return it."""
        url = link_ingest.find_url(text)
        if not url or not link_ingest.is_supported_link(url):
            return None
        return {
            "url": url,
            "caption": text.replace(url, "").strip(),
            "platform": link_ingest.is_platform_url(url),
        }

    def _disk_short_msg(self, size_label: str, required: int, avail: int) -> str:
        return (f"❌ Not enough disk space\n\nFile size: {size_label}\n"
                f"Required free space: {required} MB\nAvailable free space: {avail} MB\n\n"
                "Please free disk space or send a smaller file.")

    def _gate_link(self, chat_id: int, link: dict[str, Any],
                   message_id: Any) -> Optional[str]:
        """Two-step gate for a URL: safety + static limit + disk + confirmation."""
        if not self.cfg.link_ingest_enabled:
            self.tg.send_message(chat_id, "🔗 Link ingestion is disabled.")
            return None
        url, caption = link["url"], link["caption"]

        if link["platform"]:
            return self._process_platform_link(chat_id, url, caption, message_id)

        if not self.cfg.direct_url_download_enabled:
            self.tg.send_message(chat_id, "🔗 Direct URL download is disabled.")
            return None

        ok, reason = link_ingest.check_url_safety(url, self.cfg.block_private_urls)
        if not ok:
            log.info("upload_rejected_url url=%s reason=%s", url, reason)
            self.tg.send_message(chat_id, f"❌ Link blocked: {reason}")
            return None

        final_url, ctype, clen = url, None, None
        try:
            final_url, ctype, clen = link_ingest.head_probe(url, self.cfg.max_redirects)
        except link_ingest.LinkError:
            pass  # some servers reject HEAD; we'll stream with a byte cap instead
        ok2, reason2 = link_ingest.check_url_safety(final_url, self.cfg.block_private_urls)
        if not ok2:
            self.tg.send_message(chat_id, f"❌ Link blocked after redirect: {reason2}")
            return None

        kind = link_ingest.ext_kind(url) or link_ingest.ctype_kind(ctype) or "document"
        limit = self._type_limit_mb(kind)
        size_mb = (clen / MB) if clen else None

        if size_mb is not None and size_mb > limit:
            log.info("upload_rejected_size url=%s size_mb=%.1f limit=%d", url, size_mb, limit)
            self.tg.send_message(
                chat_id,
                f"❌ File too large\n\nType: {kind}\nSize: {int(round(size_mb))} MB\n"
                f"Limit: {limit} MB\n\nPlease send a smaller file or another link.")
            return None

        # Small known-size link: process immediately.
        if size_mb is not None and size_mb < self.cfg.large_file_confirm_mb:
            return self._download_and_process_link(
                chat_id, final_url, caption, message_id, kind, limit, url, ctype)

        # Unknown size: disk-check worst-case (limit), then stream with the cap.
        if size_mb is None:
            required = self._required_free_mb(limit)
            avail = self._free_mb()
            if avail < required:
                log.info("upload_rejected_disk url=%s (unknown size)", url)
                self.tg.send_message(chat_id, self._disk_short_msg("unknown", required, avail))
                return None
            return self._download_and_process_link(
                chat_id, final_url, caption, message_id, kind, limit, url, ctype)

        # Large known-size link within limit: disk-check, then confirm.
        avail = self._free_mb()
        required = self._required_free_mb(size_mb)
        if avail < required:
            log.info("upload_rejected_disk url=%s size_mb=%.1f required=%d avail=%d",
                     url, size_mb, required, avail)
            self.tg.send_message(
                chat_id, self._disk_short_msg(f"{int(round(size_mb))} MB", required, avail))
            return None

        self._pending_links[chat_id] = {
            "url": url, "final_url": final_url, "kind": kind, "caption": caption,
            "limit": limit, "size_mb": size_mb, "content_type": ctype,
            "created_at": time.time(), "message_id": message_id,
        }
        est = int(round(size_mb * self.cfg.disk_required_multiplier))
        log.info("large_upload_pending source=link url=%s size_mb=%.1f chat_id=%s",
                 url, size_mb, chat_id)
        self.tg.send_message(
            chat_id,
            f"⚠️ Large link detected\n\nURL: {url}\nType: {kind}\n"
            f"Size: {int(round(size_mb))} MB\nLimit: {limit} MB\n"
            f"Available disk: {self._fmt_disk(avail)}\n"
            f"Estimated temp usage: up to {est} MB\n\n"
            "Reply with PROCESS LINK to continue.")
        return None

    def _confirm_pending_link(self, chat_id: int) -> Optional[str]:
        pend = self._pending_links.pop(chat_id, None)
        if not pend:
            self.tg.send_message(chat_id, "No link is awaiting confirmation.")
            return None
        if time.time() - pend["created_at"] > self.cfg.upload_confirmation_timeout_min * 60:
            log.info("large_upload_expired source=link chat_id=%s", chat_id)
            self.tg.send_message(chat_id, "⏳ Confirmation expired. Please re-send the link.")
            return None
        size_mb = pend["size_mb"]
        required = self._required_free_mb(size_mb)
        avail = self._free_mb()
        if avail < required:  # re-check disk after confirmation
            log.info("upload_rejected_disk (recheck link) url=%s", pend["url"])
            self.tg.send_message(
                chat_id, self._disk_short_msg(f"{int(round(size_mb))} MB", required, avail))
            return None
        log.info("large_upload_confirmed source=link url=%s chat_id=%s", pend["url"], chat_id)
        return self._download_and_process_link(
            chat_id, pend["final_url"], pend["caption"], pend["message_id"],
            pend["kind"], pend["limit"], pend["url"], pend.get("content_type"))

    def _download_and_process_link(self, chat_id: int, url: str, caption: str,
                                   message_id: Any, kind: str, limit_mb: int,
                                   source_url: str, content_type: Optional[str]) -> Optional[str]:
        tmp = self._uploads_tmp()
        os.makedirs(tmp, exist_ok=True)
        base = os.path.basename(urlparse(url).path) or f"link_{int(time.time())}"
        dest = os.path.join(tmp, self._safe_filename(base))
        self.tg.send_chat_action(chat_id, "typing")
        try:
            final_url, nbytes = link_ingest.stream_download(
                url, dest, limit_mb * MB, self.cfg.max_redirects)
        except link_ingest.LinkError as exc:
            self._safe_remove(dest)
            if "max bytes" in str(exc):
                log.info("upload_rejected_size (link stream) url=%s", source_url)
                self.tg.send_message(
                    chat_id,
                    f"❌ File too large\n\nType: {kind}\nLimit: {limit_mb} MB\n\n"
                    "The link exceeded the limit while downloading.")
            else:
                self.tg.send_message(chat_id, f"⚠️ Could not download the link: {exc}")
            return None
        except requests.RequestException as exc:
            self._safe_remove(dest)
            self.tg.send_message(chat_id, f"⚠️ Could not download the link: {exc}")
            return None

        ok, reason = link_ingest.check_url_safety(final_url, self.cfg.block_private_urls)
        if not ok:
            self._safe_remove(dest)
            self.tg.send_message(chat_id, f"❌ Link blocked after redirect: {reason}")
            return None

        log.info("link downloaded url=%s final=%s bytes=%d kind=%s",
                 source_url, final_url, nbytes, kind)
        log.info("upload_processed kind=%s source=link chat_id=%s", kind, chat_id)

        meta = {
            "filename": os.path.basename(dest),
            "size": nbytes,
            "datetime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "message_id": message_id,
            "source_url": source_url,
            "final_url": final_url,
            "content_type": content_type,
        }
        if kind in ("audio", "video"):
            return self._media_file_to_transcript(chat_id, dest, meta)
        # document / image: hand the path to Claude; transcript on finalize.
        self._pending_upload = {**meta, "raw_path": dest}
        self.tg.send_message(chat_id, f"📎 Файл получен по ссылке: {meta['filename']}")
        prompt = self._file_prompt(caption, os.path.abspath(dest))
        outbox = os.path.join(self.cfg.workspace, OUTBOX_DIRNAME)
        os.makedirs(outbox, exist_ok=True)
        return prompt + OUTPUT_INSTRUCTION.format(outbox=os.path.abspath(outbox))

    def _media_file_to_transcript(self, chat_id: int, path: str,
                                  meta: dict[str, Any]) -> Optional[str]:
        """Transcribe an already-downloaded media file and write a Markdown transcript."""
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            transcript = transcribe(data, os.path.basename(path), self.cfg)
        except (TranscriptionError, requests.RequestException, OSError) as exc:
            log.error("link transcription failed: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Transcription failed: {exc}")
            if not self.cfg.file_keep_original:
                self._safe_remove(path)
            return None
        self._write_transcript({**meta, "provider": f"groq:{self.cfg.groq_model}"}, transcript)
        if not self.cfg.file_keep_original:
            self._safe_remove(path)
        self.tg.send_message(chat_id, f"📝 {transcript}")
        return transcript

    def _process_platform_link(self, chat_id: int, url: str, caption: str,
                               message_id: Any) -> Optional[str]:
        """YouTube/TikTok/etc. via yt-dlp (audio-only). Optional and off by default."""
        if not (self.cfg.ytdlp_enabled and shutil.which("yt-dlp")):
            self.tg.send_message(
                chat_id,
                "Send a direct downloadable file link or enable YTDLP_ENABLED.")
            return None
        ok, reason = link_ingest.check_url_safety(url, self.cfg.block_private_urls)
        if not ok:
            self.tg.send_message(chat_id, f"❌ Link blocked: {reason}")
            return None
        tmp = self._uploads_tmp()
        os.makedirs(tmp, exist_ok=True)
        stem = self._safe_filename("yt_audio")
        out_tmpl = os.path.join(tmp, stem + ".%(ext)s")
        self.tg.send_chat_action(chat_id, "typing")
        try:
            subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist",
                 "--max-filesize", f"{self.cfg.audio_max_mb}M", "-o", out_tmpl, url],
                check=True, capture_output=True, timeout=900)
        except (subprocess.SubprocessError, OSError) as exc:
            log.error("yt-dlp failed: %s", exc)
            self.tg.send_message(chat_id, f"⚠️ Could not fetch audio from the link: {exc}")
            return None
        produced = [os.path.join(tmp, f) for f in os.listdir(tmp) if f.startswith(stem)]
        if not produced:
            self.tg.send_message(chat_id, "⚠️ No audio was produced from the link.")
            return None
        dest = produced[0]
        log.info("upload_processed kind=audio source=ytdlp chat_id=%s", chat_id)
        meta = {
            "filename": os.path.basename(dest),
            "size": os.path.getsize(dest),
            "datetime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "message_id": message_id,
            "source_url": url,
            "final_url": url,
        }
        return self._media_file_to_transcript(chat_id, dest, meta)

    @staticmethod
    def _safe_remove(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

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
        ]
        # Link-ingested files also record their source URLs and content type.
        if meta.get("source_url"):
            lines.append(f"- Source URL: {meta.get('source_url')}")
        if meta.get("final_url"):
            lines.append(f"- Final URL: {meta.get('final_url')}")
        if meta.get("content_type"):
            lines.append(f"- Content type: {meta.get('content_type')}")
        lines += ["", "---", "", (body or "").strip(), ""]
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

        # "PROCESS FILE" / "PROCESS LINK" confirm a previously-gated large item.
        if text == "PROCESS FILE":
            text = self._confirm_pending(chat_id) or ""
            if not text:
                self._pending_upload = None
                return
        elif text == "PROCESS LINK":
            text = self._confirm_pending_link(chat_id) or ""
            if not text:
                self._pending_upload = None
                return
        else:
            # Any attachment goes through the two-step size/disk safety gate.
            att = self._classify_attachment(msg)
            if att:
                text = self._gate_attachment(chat_id, att, caption, message_id) or ""
                if not text:
                    self._pending_upload = None
                    return
            else:
                # A media/document/platform URL in the text is ingested as a file.
                link = (self._detect_ingest_link(text)
                        if (text and self.cfg.link_ingest_enabled) else None)
                if link:
                    text = self._gate_link(chat_id, link, message_id) or ""
                    if not text:
                        self._pending_upload = None
                        return
                elif not text:
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
            if "timed out" in str(exc):
                self.tg.send_message(
                    chat_id,
                    f"⏱ Task exceeded {self.cfg.claude_timeout}s and was stopped. "
                    "Moving on to the next task in the queue.")
            else:
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

        worker = threading.Thread(target=self._worker_loop, daemon=True,
                                  name="task-worker")
        worker.start()

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
                        self._handle_update(msg)  # instant ack; work is queued
                    except Exception:  # one bad update must not kill the loop
                        log.exception("error handling update %s",
                                      upd.get("update_id"))
                if not self._running:
                    break

        self._task_event.set()  # wake the worker so it can observe shutdown
        log.info("gateway stopped")
