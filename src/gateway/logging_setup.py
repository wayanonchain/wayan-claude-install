"""Logging configured for journald.

We log to stdout; systemd captures stdout/stderr into the journal, so there is
no need for a file handler or syslog socket. journald adds its own timestamp,
so the formatter stays lean.
"""
from __future__ import annotations

import logging
import sys


def setup_logging(level: str, agent: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(f"[{agent}] %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
