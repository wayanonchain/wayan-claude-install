# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — v1.1.0-alpha

### Added
- **Voice input (Groq).** Both agents transcribe Telegram voice notes via Groq
  Whisper and feed the transcript into the existing `claude -p` flow:
  `getFile` → download OGG/Opus → Groq transcription → echo 📝 → Claude → text reply.
  Text messages are unaffected; no `ffmpeg` needed.
  - New module `src/gateway/transcribe.py`; `getFile`/`download_file` on the
    Telegram client; voice routing in `app.py`.
  - New env keys: `GROQ_API_KEY`, `VOICE_ENABLED`, `VOICE_INPUT`,
    `VOICE_OUTPUT` (TTS not implemented yet), `GROQ_MODEL`, `VOICE_TIMEOUT`.
  - Unit tests in `tests/test_gateway.py` (network faked).

### Fixed
- **Groq HTTP 400 on voice notes.** Telegram delivers voice as `.oga`, which
  Groq's allow-list rejects (`ogg`/`opus` are accepted, `oga` is not). The
  upload filename is now normalized to `voice.ogg` with an explicit
  `audio/ogg` content type; bytes stay OGG/Opus (no ffmpeg). Accepted
  extensions (e.g. `.mp3`) are preserved. Covered by new tests.

## [1.0.1] - 2026-06-08

Post-deployment patch release.

### Fixed
- **systemd namespace failure (root cause).** Both gateway units declare
  `ReadWritePaths` for `/home/wayan/.config`, `/home/wayan/.claude`, and
  `/home/wayan/.cache`. systemd sets up the service's mount namespace *before*
  `ExecStart`, and if any `ReadWritePaths` target does not exist it aborts
  namespace setup — so the services failed to start on a fresh host where
  `~/.config` had not yet been created.
- `install.sh` now creates `~/.config`, `~/.cache`, and `~/.claude`
  (mode `0700`, owned by `wayan`) in `create_dirs`.
- `install.sh` adds `verify_service_dirs()`, run **before** the units are
  installed, which aborts the install if any required directory is missing.
- Both units add `ExecStartPre=/usr/bin/test -d …` guards for `~/.config` and
  `~/.claude` — a readable start-time check (the install-time creation +
  verification are what actually prevent the namespace failure).
- `scripts/healthcheck.sh` and `tests/verify.sh` now assert the home
  directories exist.

## [1.0.0] - 2026-06-08

Initial deployable release (EdgeLab Day 1 methodology).

### Added
- Two independent Claude Code agents: **Jupiter** (main daily) and **Uran**
  (backup / root-fix), each with its own Telegram bot, workspace, env file,
  and systemd service.
- Python **Telegram Gateway** (long polling) bridging Telegram ⇄ Claude Code
  headless mode (`claude -p`): message loop, graceful SIGTERM/SIGINT shutdown,
  journald logging, per-chat allowlist, 4096-char message splitting.
- Idempotent `install.sh`: base packages, Node.js 22, Claude Code (per user),
  `wayan` user, per-agent Python venv + dependency install, gateway deploy,
  systemd services, scoped sudoers, and a Claude login gate.
- Lifecycle scripts: `cleanup.sh`, `update.sh`, `uninstall.sh`,
  `healthcheck.sh`; plus `tests/verify.sh`.
