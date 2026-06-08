"""Minimal Telegram Bot API client using long polling.

Only the handful of methods the gateway needs: getMe, getUpdates (long poll),
sendChatAction, sendMessage (with 4096-char splitting).
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

log = logging.getLogger("telegram")

TELEGRAM_MAX_LEN = 4096


class TelegramError(Exception):
    """Raised when the Telegram API returns ok=false."""


class TelegramClient:
    def __init__(self, token: str, poll_timeout: int = 50) -> None:
        self._token = token
        self._base = f"https://api.telegram.org/bot{token}"
        self.poll_timeout = poll_timeout
        self._session = requests.Session()

    def _call(self, method: str, params: dict[str, Any] | None = None,
              timeout: int = 30) -> Any:
        resp = self._session.post(f"{self._base}/{method}", json=params or {},
                                  timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise TelegramError(f"{method} failed: {data}")
        return data["result"]

    def get_me(self) -> dict[str, Any]:
        return self._call("getMe")

    def get_updates(self, offset: int) -> list[dict[str, Any]]:
        # Network timeout must exceed the long-poll timeout, or requests aborts
        # the connection before Telegram has a chance to reply.
        return self._call(
            "getUpdates",
            {"offset": offset, "timeout": self.poll_timeout,
             "allowed_updates": ["message"]},
            timeout=self.poll_timeout + 15,
        )

    def get_file(self, file_id: str) -> dict[str, Any]:
        """Resolve a file_id to a file object containing 'file_path'."""
        return self._call("getFile", {"file_id": file_id})

    def download_file(self, file_path: str) -> bytes:
        """Download a file by the file_path returned from getFile."""
        url = f"https://api.telegram.org/file/bot{self._token}/{file_path}"
        resp = self._session.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        try:
            self._call("sendChatAction", {"chat_id": chat_id, "action": action})
        except Exception as exc:  # non-critical; never block the reply on this
            log.debug("sendChatAction failed: %s", exc)

    def send_document(self, chat_id: int, file_path: str,
                      caption: str | None = None) -> dict[str, Any]:
        """Upload a local file to the chat as a Telegram document."""
        data: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption[:1024]
        with open(file_path, "rb") as fh:
            files = {"document": (os.path.basename(file_path), fh)}
            resp = self._session.post(f"{self._base}/sendDocument",
                                      data=data, files=files, timeout=180)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("ok"):
            raise TelegramError(f"sendDocument failed: {result}")
        return result["result"]

    def send_message(self, chat_id: int, text: str) -> None:
        for chunk in split_message(text or "(empty response)"):
            self._call("sendMessage", {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            })


def split_message(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    """Split text into <=limit chunks, preferring newline boundaries."""
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    chunks.append(remaining)
    return chunks
