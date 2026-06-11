"""Wayan Telegram Gateway.

A small, dependency-light bridge that connects a single Telegram bot to
Claude Code running in headless mode (`claude -p`). One process per agent
(Jupiter or Uran); all behaviour is driven by environment variables so the
same code runs both agents with separate configuration.
"""

__version__ = "1.1.0a11"
