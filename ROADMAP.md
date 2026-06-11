# Wayan Agents — Roadmap & Architecture

> **Security note:** this is a public repository. No host IPs, bot tokens, chat
> IDs, or credentials appear here. Operational state is described generically.

---

## 1. Current status (as of v1.0.1)

Production deployment is **live and validated** on an Ubuntu 22.04 VPS.

| Component | State |
| --- | --- |
| Installer (`install.sh`) | ✅ validated end-to-end on VPS (idempotent re-run clean) |
| `wayan` user + workspaces | ✅ present (`/home/wayan/.claude-lab/{jupiter,uran}`) |
| Jupiter agent | ✅ running (`wayan-jupiter.service`) |
| Uran agent | ✅ running (`wayan-uran.service`) |
| Telegram | ✅ connected (separate bot per agent, long polling) |
| Claude Code | ✅ authenticated for `wayan`, headless `claude -p` |
| Per-agent venvs + deps | ✅ `/opt/wayan-{jupiter,uran}/venv` |
| sudoers (Uran grants) | ✅ installed + `visudo`-validated |
| systemd home-dir fix | ✅ `~/.config`, `~/.cache`, `~/.claude` created + verified |

Released: **v1.0.0** (initial deployable) → **v1.0.1** (namespace/home-dir fix).

---

## 2. Current architecture

```
                       Telegram (2 separate bots)
                ┌──────────────┐      ┌──────────────┐
                │ Jupiter bot  │      │   Uran bot   │
                └──────┬───────┘      └──────┬───────┘
                       │ long poll           │ long poll
        ┌──────────────▼─────────┐  ┌────────▼─────────────────┐
        │ wayan-jupiter.service  │  │  wayan-uran.service       │
        │  /opt/wayan-jupiter    │  │  /opt/wayan-uran          │
        │  venv → python -m      │  │  venv → python -m         │
        │        gateway         │  │        gateway            │
        └──────────────┬─────────┘  └────────┬─────────────────┘
                       │ subprocess           │ subprocess
                       ▼ claude -p            ▼ claude -p
        ┌──────────────────────────────────────────────────────┐
        │ Claude Code (headless, per-user 'wayan' auth)          │
        │ cwd = workspace → reads CLAUDE.md / USER.md            │
        └──────────────────────────────────────────────────────┘

  Workspaces: /home/wayan/.claude-lab/{jupiter,uran}/  (CLAUDE.md, USER.md)
  Config:     /etc/wayan-{jupiter,uran}.env            (token, perms, allowlist)
  Privilege:  /etc/sudoers.d/wayan-agents              (Uran: restart/journal)
```

### Gateway internals (`src/gateway/`)
- `__main__.py` — entry point (`python -m gateway`): load config → logging → run
- `config.py` — env-driven config (token, workspace, allowlist, timeouts, perms)
- `telegram_api.py` — long-poll Bot API client + 4096-char splitting
- `claude_runner.py` — `claude -p --output-format text` in the workspace cwd
- `app.py` — poll → Claude → reply loop, SIGTERM/SIGINT graceful stop, allowlist
- `logging_setup.py` — journald-friendly stdout logging

### Key properties
- **Two fully independent agents** — same code, separate token/workspace/service/env.
- **Idempotent installer** — safe re-runs; never clobbers env secrets or edited templates.
- **Headless Claude** — one-shot `claude -p`, `--continue` for in-process continuity.
- **Hardened units** — `ProtectSystem=full`, `ProtectHome=read-only`,
  scoped `ReadWritePaths`, `NoNewPrivileges`.
- **Permission mode** — both agents on `acceptEdits` (env-switchable per agent).

### Known limitations (targets for v1.1.0)
- Uran has no automated repair behavior yet (acts like a second Jupiter).
- Health checks are presence-based, not live liveness.
- Updates are manual (`scripts/update.sh`).
- Agent count is hardcoded to two.
- Text only — no voice.

---

## 3. v1.1.0 milestones

Sequenced by dependency and risk. Each milestone ships behind config flags and
must pass `bash -n` + gateway tests + a VPS smoke test before release.

### M1 — Voice support (Groq)
**Goal:** accept Telegram voice notes; transcribe via Groq; answer through Claude.

- Telegram `voice`/`audio` updates → `getFile` → download `.ogg`.
- Transcribe with Groq (Whisper-class model) via `GROQ_API_KEY`.
- Feed transcript to the existing `claude -p` path; reply as text.
- Optional: TTS reply (later sub-step).
- New deps: `requests` (have it) + audio handling; possibly `ffmpeg` package.
- New env: `GROQ_API_KEY`, `VOICE_ENABLED`, `GROQ_MODEL`.
- **Done when:** a voice note round-trips to a Claude text answer on the VPS.

### M2 — Uran watchdog  *(was Phase 4)*
**Goal:** Uran autonomously detects and repairs a downed Jupiter.

- Watchdog loop (thread or `systemd` timer) checking `is-active wayan-jupiter`.
- On failure: read `journalctl -u wayan-jupiter` (via existing sudoers), attempt
  restart, escalate to operator over Uran's Telegram bot with the cause.
- Backoff + flap protection; structured incident messages.
- **Done when:** killing Jupiter triggers Uran detect → restart → notify within a bounded window.

### M3 — Health monitoring  *(was Phase 5)*
**Goal:** real liveness, not just file presence.

- Active checks: process alive, Telegram `getMe` reachable, last-update heartbeat.
- `systemd` `WatchdogSec` + `sd_notify` heartbeat from the gateway.
- Upgrade `healthcheck.sh` to report live status; optional scheduled self-report.
- **Done when:** healthcheck distinguishes "running+connected" from "running+stuck".

### M4 — Auto update
**Goal:** safe, scheduled updates from GitHub.

- `systemd` timer running `update.sh`; pull only when a newer tag exists.
- Pre-update snapshot of env/templates; health gate + auto-rollback on failure.
- Respect idempotency; never overwrite secrets.
- **Done when:** a new tag is picked up, applied, services restarted, verified — or rolled back.

### M5 — Multi-agent scaling
**Goal:** move from two hardcoded agents to N declarative agents.

- `systemd` template unit `wayan-agent@.service`; per-agent env `wayan-<name>.env`.
- Agent registry/config consumed by `install.sh` to provision any list of agents.
- Generalize cleanup/uninstall/healthcheck to enumerate agents dynamically.
- **Done when:** adding a third agent is a config edit + install re-run, no code changes.

---

## 4. Suggested sequencing

```
v1.0.1 (done)
   └─ M2 Uran watchdog ──┐  (highest operational value; uses existing sudoers)
   └─ M3 Health monitor ─┴─ pair well together (liveness feeds watchdog)
   └─ M1 Voice (Groq) ─────  independent feature; can run in parallel
   └─ M4 Auto update ──────  after M3 (needs health gate for safe rollback)
   └─ M5 Multi-agent ──────  last; refactors installer + units
```

Recommended first target for v1.1.0-alpha: **M2 + M3** (make the pair resilient
and observable), then **M1** as the headline feature.

---

## 6. Stable skills system (delivered)

A read-only, proposal-based skills layer — Anthropic-style `SKILL.md` playbooks
that the agents follow, **without any autonomous self-editing**.

- **Six initial skills:** `onchain-alpha`, `content-engine`, `file-analyst`,
  `server-ops`, `security-check`, `agent-reviewer`.
- **Read-only in production.** Agents never edit `SKILL.md` or their own
  `CLAUDE.md`. This is the core safety constraint: production instructions are
  immutable to the agents themselves.
- **Proposals, not mutations.** Improvements go to `skills/_proposals/` with a
  fixed format (skill, reason, observed problem, suggested diff, risk level,
  rollback note). A human reviews and applies. Nothing is auto-applied.
- **Pattern logs.** Per-agent `logs/{successful,failed}` capture notable
  outcomes to inform the `agent-reviewer` skill.
- **No new dependencies, no external API calls.** Plain Markdown; the installer
  copies skills into each workspace no-clobber and creates the logs dirs.

### Future (guarded) extensions
- Optional, explicitly-configured external data sources for `onchain-alpha`.
- A human-driven "apply proposal" helper (still never automatic).
- Skill usage metrics feeding `agent-reviewer`.

## 7. Day 2 orchestration layer (implemented — foundation)

A stable orchestration layer that keeps the agents consistent and improvable
without any autonomous self-editing. This is the foundation the rest of Day 2
builds on.

- **`rules/`** — hard rules (safety, skill-routing, services-map).
- **`learnings/`** — captured user feedback (`inbox/` → `reviewed/`).
- **`memory/`** — tiered context (`hot` / `warm` / `cold`).
- **`mapping/`** — infrastructure, services, accounts (user-customized; secrets
  stay out of git via `accounts.md`).
- **`skill-lab/`** — experimental new-skill proposals.
- **Manual learning loop:** feedback → inbox → review → propose → **approve** →
  apply. The agent never edits `CLAUDE.md`, `rules/`, `memory/`, or `SKILL.md`
  on its own.
- Copied into both workspaces by the installer (no-clobber); no new
  dependencies, no external API calls.

### Future (optional, disabled by default)
- **Autonomous auto-fix** — letting the agent apply approved-class changes
  without a per-change prompt. Explicitly **off by default**; opt-in only, and
  only after the manual loop has proven a change class safe.

## 8. Profession packs (future modular add-ons)

The framework is profession-agnostic; **profession packs** adapt it by swapping
Markdown only (skills, memory seeds, rules, mapping) — the gateway, queue,
storage policy, permissions, and memory infra stay shared. Eight pack designs
are documented in [docs/PROFESSION_PACKS.md](docs/PROFESSION_PACKS.md):
Crypto/Onchain Analyst (shipped as the default), Content Creator, Founder,
Developer/DevOps, Researcher/Student, Coach/Consultant, Real-Estate/Relocation,
SMM/Community Manager.

**Adding a new pack** = 2–4 new `SKILL.md` files + routing lines in `CLAUDE.md`
+ `cold.md` seed + domain rules + mapping entries; deployed via the normal
installer/apply-templates flow. See the recipe at the end of
[PROFESSION_PACKS.md](docs/PROFESSION_PACKS.md). Future work: ship packs as
selectable installer options (`WAYAN_PACK=creator install.sh`).

## 9. Cross-cutting concerns

- **Secrets:** keep tokens/keys in `/etc/wayan-*.env` (mode 0640, root:wayan); never in git.
- **Least privilege:** revisit Uran's perm mode (`acceptEdits` today) and sudoers
  scope as the watchdog gains power.
- **Allowlist:** set `TELEGRAM_ALLOWED_CHAT_IDS` per agent before exposing voice/auto-update.
- **Testing:** every milestone adds to `tests/verify.sh` and the gateway test suite.
- **Versioning:** SemVer; features land in `1.1.0`, fixes as `1.0.x`/`1.1.x`.
