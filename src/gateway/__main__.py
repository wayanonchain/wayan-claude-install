"""Entry point: `python -m gateway`.

Loads configuration from the environment (the agent's env file, supplied by
systemd via EnvironmentFile), sets up journald logging, and runs the loop.
"""
from __future__ import annotations

import sys

from .app import Gateway
from .config import ConfigError, load_config
from .logging_setup import setup_logging


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    setup_logging(cfg.log_level, cfg.agent)
    Gateway(cfg).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
