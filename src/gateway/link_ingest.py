"""Safe ingestion of files from URLs.

Telegram bots cannot download files larger than ~20 MB via getFile, so large
media is ingested from a direct URL instead. This module provides the network
and safety primitives; the orchestration (limits, disk, confirmation) lives in
the gateway. Network functions are deliberately small seams so they can be
faked in tests.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import requests

log = logging.getLogger("link")

# Any scheme://… — so we can detect (and then reject) ftp:// / file:// too.
URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s<>()]+")

DIRECT_EXT_KIND = {
    ".mp4": "video", ".mov": "video", ".webm": "video",
    ".m4a": "audio", ".mp3": "audio", ".wav": "audio", ".ogg": "audio",
    ".pdf": "document", ".txt": "document", ".csv": "document",
}
PLATFORM_HOSTS = (
    "youtube.com", "youtu.be", "youtube-nocookie.com", "m.youtube.com",
    "tiktok.com", "instagram.com", "vimeo.com",
)
_CONTENT_TYPE_KIND = (
    ("video/", "video"), ("audio/", "audio"),
    ("application/pdf", "document"), ("text/", "document"),
    ("image/", "image"),
)

_UA = {"User-Agent": "WayanGateway/1.0"}


class LinkError(Exception):
    """Raised on download/HEAD failures or when a byte cap is exceeded."""


def find_url(text: str) -> str | None:
    m = URL_RE.search(text or "")
    return m.group(0).rstrip(".,;)]") if m else None


def is_platform_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in PLATFORM_HOSTS)


def ext_kind(url: str) -> str | None:
    path = urlparse(url).path.lower()
    for ext, kind in DIRECT_EXT_KIND.items():
        if path.endswith(ext):
            return kind
    return None


def ctype_kind(content_type: str | None) -> str | None:
    c = (content_type or "").lower()
    for prefix, kind in _CONTENT_TYPE_KIND:
        if c.startswith(prefix):
            return kind
    return None


def is_supported_link(url: str) -> bool:
    """A URL we will ingest as a file: a direct media/doc extension or a platform URL."""
    return ext_kind(url) is not None or is_platform_url(url)


def _ip_is_forbidden(ip: ipaddress._BaseAddress) -> bool:
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def check_url_safety(url: str, block_private: bool = True) -> tuple[bool, str]:
    """Return (ok, reason). Enforces http/https and blocks private/local hosts
    (including hostnames that resolve to private IPs — DNS-rebinding defence)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False, f"unsupported scheme: {p.scheme or '(none)'}"
    host = (p.hostname or "").lower()
    if not host:
        return False, "no host"
    if host in ("localhost",) or host.endswith(".localhost"):
        return (False, "localhost blocked") if block_private else (True, "")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if block_private and _ip_is_forbidden(ip):
            return False, f"private/forbidden IP: {host}"
        return True, ""

    if block_private:
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError:
            return False, f"cannot resolve host: {host}"
        for info in infos:
            addr = info[4][0]
            try:
                rip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if _ip_is_forbidden(rip):
                return False, f"host resolves to private IP: {host} -> {addr}"
    return True, ""


def head_probe(url: str, max_redirects: int = 5) -> tuple[str, str | None, int | None]:
    """Best-effort HEAD: returns (final_url, content_type, content_length|None)."""
    sess = requests.Session()
    sess.max_redirects = max_redirects
    try:
        r = sess.head(url, allow_redirects=True, timeout=20, headers=_UA)
    except requests.RequestException as exc:
        raise LinkError(f"HEAD failed: {exc}") from exc
    clen = r.headers.get("Content-Length")
    clen = int(clen) if clen and clen.isdigit() else None
    ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip() or None
    return r.url, ctype, clen


def stream_download(url: str, dest: str, max_bytes: int,
                    max_redirects: int = 5) -> tuple[str, int]:
    """Stream url to dest, aborting if more than max_bytes are received (even when
    Content-Length is absent). Returns (final_url, bytes_written)."""
    sess = requests.Session()
    sess.max_redirects = max_redirects
    written = 0
    with sess.get(url, stream=True, timeout=60, allow_redirects=True,
                  headers=_UA) as r:
        r.raise_for_status()
        final_url = r.url
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise LinkError("exceeded max bytes")
                fh.write(chunk)
    return final_url, written
