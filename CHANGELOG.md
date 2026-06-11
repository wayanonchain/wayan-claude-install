# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — v1.1.0-alpha

### Fixed
- **Task queue + robust video handling.** The gateway now acks every incoming
  task instantly (`✅ Task received. Queue position: N`) and processes tasks
  sequentially via a worker thread; Claude calls stay serialized behind a global
  lock (one `--continue` session per workspace — true parallelism deferred).
  New `/queue` and `/cancel` commands; per-task timeout replies clearly
  (`⏱ … Moving on to the next task`) and the queue continues after timeout or
  crash — no silent failure paths. Videos (`video`, `video_note`, video-MIME
  documents) get an immediate `🎥 Video received…` ack before size gating;
  oversized videos get the direct-link advice. `CLAUDE_TASK_TIMEOUT_SEC` added
  as the preferred timeout name (falls back to `CLAUDE_TIMEOUT`). 12 regression
  tests (rapid multi-message ordering, /queue, /cancel, timeout-continue,
  crash-notify, video ack variants).

### Added
- **Repo-first gateway deployment workflow.** GitHub is now the explicit single
  source of truth for `src/gateway/` (motivated by 1.1.0a11 existing on the VPS
  before the repo — reconciled in `6fcaadb`). New `scripts/deploy-gateway.sh`:
  `--check` (drift report, PASS/FAIL, **file names only** — never contents or
  secrets), `--dry-run` (full preview, changes nothing), and deploy mode that
  refuses a dirty tree (override: `--allow-dirty`), creates timestamped
  `gateway.bak.YYYYMMDD-HHMMSS` backups, syncs both `/opt` agent trees
  (`chown wayan:wayan`), runs a per-venv import sanity check, optionally
  restarts + verifies services (`--restart`), and re-verifies checksums after
  deploy. By construction it never touches env files, secrets, `ov.conf`,
  OpenViking, venvs, or workspaces — and aborts if anything secret-shaped
  appears inside `src/gateway/`. `scripts/update.sh` rewritten repo-first:
  pull → full test suite → drift check, deploying **only** with explicit
  `--deploy [--restart]` (legacy installer path kept as `--full`). New
  `docs/DEPLOYMENT.md` (workflow, rollback, drift checks, secret hygiene);
  README "Deploy / Update" section; ROADMAP M4 updated + M6 host-hardening
  milestone added. 8 new tests (sandboxed repo + fake `/opt` trees): syntax,
  check PASS/drift, dry-run immutability, dirty-tree refusal, backup creation,
  env-file untouchability.
- **Visual video analysis (gateway 1.1.0a11).** With `VIDEO_VISUAL_ANALYSIS=true`
  and ffmpeg installed, videos are analyzed **visually as well as by audio**:
  the gateway downloads the video once, gets a Groq audio transcript, extracts
  N evenly-spaced keyframes via per-frame `ffmpeg -ss` calls (low-RAM safe,
  downscaled + JPEG-compressed), has Claude visually inspect every frame, and
  replies with one merged `## Audio / ## Visual / ## Combined` summary. Frames
  are written to a per-video dir under `uploads/tmp/` and **deleted right after
  the reply** (`VIDEO_FRAME_DEBUG_KEEP` for debugging); the raw video follows
  the existing minimal-storage policy. Every degradation (no audio track,
  ffmpeg missing, extraction failure/timeout) is reported to the user and
  logged — no silent paths. Off by default; when off (or ffmpeg is absent) the
  legacy audio-only path is unchanged. New `src/gateway/video_frames.py`;
  new env: `VIDEO_VISUAL_ANALYSIS`, `VIDEO_FRAMES`, `VIDEO_FRAME_MAX_WIDTH`,
  `VIDEO_FRAME_JPEG_QUALITY`, `VIDEO_FRAME_EXTRACTION_TIMEOUT_SEC`,
  `FFMPEG_PATH`, `VIDEO_FRAME_DEBUG_KEEP`. **Live-tested in production
  2026-06-11**: full path (download → transcript → 5 frames → merged reply →
  cleanup) verified in journald; tmp frames and raw video both cleaned.
- **Public-template & beginner docs.** New `docs/MAC_SETUP.md` (control-machine
  model, SSH keys, `~/.ssh/config`, Remote-SSH), `docs/PUBLIC_TEMPLATE_GUIDE.md`
  (fork & customize; never-commit list), `docs/COSTS_AND_SERVICES.md` (services +
  official pricing links), `docs/TERMS_GLOSSARY.md` (plain-English terms). README
  gains a *Getting started* section (installation paths A/B/C + 9-step beginner
  flow + docs index). Removed a hardcoded server IP default from
  `export-knowledge.sh` (now requires `WAYAN_VPS`) for public-template safety.
- **Role-based agent permission profiles (persistent).** Per-agent
  `templates/<agent>/claude-settings.json` deployed to
  `<workspace>/.claude/settings.json`: read-only diagnostics + research + git
  inspect + the OpenViking memory MCP tools are allow-listed; dangerous ops
  (git push, ssh, sudo, rm, chmod/chown, service stop/disable, docker down, apt,
  reboot/shutdown, …) are gated; and `deny` rules enforce **no self-editing** of
  `CLAUDE.md`/`USER.md`/`rules`/`memory`/`mapping`/`skills`. Uran also allows
  scoped service restarts + `docker compose restart openviking`. Installer
  deploys them no-clobber; `apply-templates.sh` updates them with a timestamped
  backup. Docs: `docs/PERMISSIONS.md`. Never touches env files, `ov.conf`, or
  keys.
- **Safe link ingestion for large files.** Since Telegram bots can't download
  files over ~20 MB, large media is ingested from a URL instead. Direct file
  URLs (`.mp4/.mov/.m4a/.mp3/.wav/.ogg/.webm/.pdf/.txt/.csv`) are `HEAD`-probed,
  classified, size/disk-gated (same limits as uploads), and **streamed with a
  hard byte cap** (aborts past the limit even without Content-Length). Large
  links require a `PROCESS LINK` confirmation (per-chat, expiring, disk
  re-checked). Optional `YTDLP_ENABLED` fetches **audio-only** from
  YouTube/TikTok/etc. via yt-dlp → Groq transcript. SSRF protection blocks
  non-http(s) and private/local hosts (incl. DNS-rebinding), caps redirects, and
  re-checks the post-redirect URL. Telegram uploads over 20 MB now tell the user
  to send a link. Link transcripts record source/final URL + content type. New
  env: `LINK_INGEST_ENABLED`, `DIRECT_URL_DOWNLOAD_ENABLED`, `YTDLP_ENABLED`,
  `MAX_REDIRECTS`, `BLOCK_PRIVATE_URLS`. New `src/gateway/link_ingest.py`; docs
  in STORAGE_POLICY; tests cover direct/large/oversized/streaming-guard/SSRF/
  yt-dlp paths.
- **Safe large-upload confirmation flow.** Uploads now pass a two-step gate
  before download: (1) a per-type static size limit
  (`VIDEO_MAX_MB`/`AUDIO_MAX_MB`/`DOCUMENT_MAX_MB`/`IMAGE_MAX_MB`, fallback
  `FILE_MAX_MB`), and (2) a disk-availability check
  (`size * DISK_REQUIRED_MULTIPLIER + DISK_MIN_FREE_MB` must be free). Files
  ≥ `LARGE_FILE_CONFIRM_MB` warn the user (type/size/limit/free-disk/est-usage)
  and wait for a literal `PROCESS FILE` reply; pending state expires after
  `UPLOAD_CONFIRMATION_TIMEOUT_MIN` and disk is re-checked on confirm. Oversized
  or disk-short files are rejected without downloading; small files process
  immediately. Structured logs: `large_upload_pending/confirmed/expired`,
  `upload_rejected_size/disk`, `upload_processed`. New env keys + STORAGE_POLICY
  docs (incl. the 20 MB Telegram bot-download limit → send links for big video).
- **Minimal-storage policy for uploads.** Heavy uploads are temporary; long-term
  knowledge is Markdown. Raw files land in `uploads/tmp/`, are transcribed
  (audio→Groq) or analyzed (documents→Claude) into a Markdown transcript in
  `transcripts/` (with metadata: original filename, size, timestamp, agent,
  Telegram message id, provider/model), then the raw file is deleted unless
  `FILE_KEEP_ORIGINAL=true`. New env: `FILE_KEEP_ORIGINAL` (false),
  `FILE_RETENTION_HOURS` (24), `TRANSCRIPTS_ENABLED` (true), `TRANSCRIPTS_DIR`,
  `UPLOADS_TMP_DIR`. New `scripts/cleanup-uploads.sh` sweeps aged `uploads/tmp`
  files only (never transcripts/memory/rules/skills/learnings/mapping/env/creds);
  optional `wayan-cleanup.timer` ships **disabled by default**. Installer creates
  `uploads/tmp` + `transcripts` per agent. `.gitignore` blocks `uploads/` and
  root `transcripts/`. Docs: `docs/STORAGE_POLICY.md`. Tests cover env defaults,
  cleanup safety, transcript creation, and raw-file deletion.
- **Day 2 orchestration layer.** New `orchestration/` tree copied into each
  workspace: `rules/` (safety, skill-routing, services-map), `learnings/`
  (`inbox/` → `reviewed/`), `memory/` (`hot`/`warm`/`cold`), `mapping/`
  (infrastructure, services, accounts.example), and `skill-lab/`. Adds a
  `## Day 2 Orchestration` checklist to both `CLAUDE.md` templates and a manual
  learning loop (feedback → inbox → review → propose → **approve** → apply).
  **No autonomous auto-fix**; agents never edit production rules/memory/skills/
  `CLAUDE.md` without explicit approval. Installer copies it no-clobber; real
  `accounts.md` is git-ignored. Guide: `docs/DAY2_ORCHESTRATION.md`. No new
  dependencies, no external API calls.
- **Skill chaining.** The `## Skills Usage` section now tells agents to chain
  multiple skills for cross-domain tasks (read all relevant `SKILL.md` first,
  apply in order) — e.g. an uploaded token report + "make an X post" routes
  file-analyst → onchain-alpha → content-engine instead of stopping at one.
- **Automatic skills selection.** The agent templates now include a
  `## Skills Usage` section that classifies the task and routes it to the right
  `SKILL.md` before answering. New `scripts/apply-templates.sh` pushes updated
  `CLAUDE.md` into existing workspaces with a timestamped backup
  (`CLAUDE.md.bak.<ts>`), without touching `USER.md`, env files, skills, or
  credentials. The installer stays no-clobber by default.
- **Stable skills system.** Read-only `SKILL.md` playbooks copied into each
  workspace: `onchain-alpha`, `content-engine`, `file-analyst`, `server-ops`,
  `security-check`, `agent-reviewer`. Agents use skills but **never self-edit**
  them or their `CLAUDE.md`; improvements go through human-reviewed proposals in
  `skills/_proposals/` (nothing auto-applied). Per-agent `logs/{successful,failed}`
  for notable patterns. Installer copies skills no-clobber + creates logs dirs;
  healthcheck/verify and repo tests assert the layout. No new dependencies, no
  external API calls.
- **File attachments (documents & photos).** Sending a document or photo is no
  longer ignored: the gateway downloads it into `<workspace>/uploads/` and hands
  Claude the saved path (the message `caption` becomes the task). Photos use the
  largest size; filenames are sanitized; size capped by `FILE_MAX_MB`.
  - New env keys: `FILES_ENABLED` (default `true`), `FILE_MAX_MB` (default `20`).
  - New `reply sent to chat_id=… (N chars)` log line for delivery visibility.
  - Unit tests for download, prompt building, photo selection, limits, routing.
- **File output (outbox → Telegram).** Agents can now return files: anything
  Claude writes into `<workspace>/outbox/` during a run is delivered back to the
  user as a Telegram document. Enables file-in → file-out task flows. The outbox
  is snapshotted before each run; only new/modified files are sent (no resends).
  - `telegram_api.send_document`; outbox snapshot/deliver in `app.py`; the file
    prompt now also tells Claude where to save deliverables.
  - CLAUDE.md templates document the `uploads/` ↔ `outbox/` convention.
  - Unit tests for delivery, no-resend, and text-task → file output.

### Changed
- **Deterministic file-analysis prompt.** Uploaded files now produce an explicit
  read-then-act instruction (`You MUST first read and inspect the file located
  at: <abs path>` … `If the file cannot be read, explain why.`) instead of
  relying on Claude to open the path on its own. The `caption` is still the task;
  an absolute path is used; works for documents, images, and future file types.
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
