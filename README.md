# Wayan Claude Agents — Installer (Day 1)

A clean, self-contained installer that provisions **two Claude Code agents** on
an Ubuntu VPS, following the EdgeLab "Day 1" methodology.

> This is an independent installer. It is **not** tied to any previous
> `wayan_pirat_bot` setup.

> **New here?** Start with [Terms Glossary](docs/TERMS_GLOSSARY.md) and
> [Costs & Services](docs/COSTS_AND_SERVICES.md), then come back to *Getting
> started* below.

---

## Getting started

The agents run on an **Ubuntu VPS** (a rented Linux server), **not** on your
laptop. You install and operate them over SSH.

### Installation paths

- **A. Mac user → VPS install (recommended for beginners).** Use your Mac to
  connect to a fresh VPS and run the installer there. Full walkthrough:
  [docs/MAC_SETUP.md](docs/MAC_SETUP.md), then the beginner flow below. *(Windows/
  Linux desktops work the same way — you just need `git` + `ssh`.)*
- **B. Direct VPS install.** Already on an Ubuntu VPS? Skip the Mac steps and run
  the installer one-liner in [§6](#6-install-on-the-vps).
- **C. Fork & customize this repo.** Want your own branded agents? Fork it and
  adapt the templates/skills/mapping: [docs/PUBLIC_TEMPLATE_GUIDE.md](docs/PUBLIC_TEMPLATE_GUIDE.md).

### Beginner flow (path A)

1. **Create accounts:** GitHub, Telegram, Anthropic (Claude), Groq, OpenAI — see
   [Costs & Services](docs/COSTS_AND_SERVICES.md).
2. **Create a VPS** (Ubuntu 22.04/24.04, 2 GB RAM recommended). Note its IP +
   root password.
3. **Connect from your Mac:** [docs/MAC_SETUP.md](docs/MAC_SETUP.md)
   (`ssh root@SERVER_IP`).
4. **Run the installer** on the VPS ([§6](#6-install-on-the-vps)).
5. **Log in to Claude** as the `wayan` user ([§7](#7-authorize-claude-code)).
6. **Add Telegram bot tokens** ([§8](#8-telegram-bot-token--jupiter), [§9](#9-telegram-bot-token--uran)).
7. **Add your Groq key** for voice ([§13](#13-voice-input-groq--v110)).
8. **Add OpenViking memory** (optional but recommended):
   [docs/OPENVIKING_MEMORY.md](docs/OPENVIKING_MEMORY.md).
9. **Test Jupiter & Uran** — message the bots; run `scripts/healthcheck.sh`
   ([§10](#10-verify)).

### Documentation index

| Doc | What it covers |
| --- | --- |
| [MAC_SETUP.md](docs/MAC_SETUP.md) | Connect from a Mac (SSH keys, `~/.ssh/config`, Remote-SSH) |
| [COSTS_AND_SERVICES.md](docs/COSTS_AND_SERVICES.md) | What you need and roughly what it costs |
| [TERMS_GLOSSARY.md](docs/TERMS_GLOSSARY.md) | Plain-English definitions (SSH, VPS, API key, …) |
| [PUBLIC_TEMPLATE_GUIDE.md](docs/PUBLIC_TEMPLATE_GUIDE.md) | Fork & customize; what to never commit |
| [DAY2_ORCHESTRATION.md](docs/DAY2_ORCHESTRATION.md) | Rules / learnings / memory / mapping / skill-lab |
| [PERMISSIONS.md](docs/PERMISSIONS.md) | Role-based agent permission profiles |
| [STORAGE_POLICY.md](docs/STORAGE_POLICY.md) | Minimal storage, uploads, transcripts, large links |
| [OPENVIKING_MEMORY.md](docs/OPENVIKING_MEMORY.md) | Long-term semantic memory |
| [KNOWLEDGE_EXPORT.md](docs/KNOWLEDGE_EXPORT.md) | Exporting approved Markdown knowledge to Git |

---

## 1. What we install

- **Jupiter** — the main daily agent (code, Telegram, projects).
- **Uran** — the backup / root-fix agent (repairs Jupiter, reads logs,
  restarts services, second independent channel).
- Node.js 22, Python 3, Claude Code, and supporting packages.
- Two `systemd` services, env files, a workspace, and a scoped `sudoers` rule.

---

## 2. Architecture

```
Ubuntu VPS (22.04 / 24.04)
└── user: wayan
    ├── /home/wayan/.claude-lab/
    │   ├── jupiter/   (CLAUDE.md, USER.md)   ← main agent workspace
    │   └── uran/      (CLAUDE.md, USER.md)   ← backup agent workspace
    ├── /opt/wayan-jupiter   ← Jupiter code/tools
    ├── /opt/wayan-uran      ← Uran code/tools
    ├── /etc/wayan-jupiter.env   (TELEGRAM_BOT_TOKEN=…)
    ├── /etc/wayan-uran.env      (TELEGRAM_BOT_TOKEN=…)
    ├── /etc/sudoers.d/wayan-agents
    └── systemd:
        ├── wayan-jupiter.service
        └── wayan-uran.service
```

---

## 3. Why two agents

A single agent is a single point of failure. If it crashes, hangs, or its
service dies, nobody can recover it remotely.

- **Jupiter** does the daily work.
- **Uran** is an independent watchdog with its own Telegram bot, its own
  service, and just enough `sudo` to inspect logs and restart Jupiter.

If Jupiter goes down, you message Uran and it brings Jupiter back.

---

## 4. Prerequisites

- A fresh Ubuntu **22.04** or **24.04** VPS.
- `root` (or `sudo`) access.
- Two Telegram bot tokens (one per agent — see sections 8–9).
- An Anthropic account to log in to Claude Code.

---

## 5. Local preparation (GitHub)

```bash
git clone https://github.com/wayanonchain/wayan-claude-install.git
cd wayan-claude-install
# inspect install.sh and scripts/ before running anything on a VPS
```

Repository layout:

```
wayan-claude-install/
├── README.md
├── install.sh
├── scripts/
│   ├── cleanup.sh
│   ├── update.sh
│   ├── uninstall.sh
│   └── healthcheck.sh
├── templates/
│   ├── jupiter/{CLAUDE.md,USER.md}
│   └── uran/{CLAUDE.md,USER.md}
├── systemd/
│   ├── wayan-jupiter.service
│   └── wayan-uran.service
└── tests/
    └── verify.sh
```

---

## 6. Install on the VPS

One-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/wayanonchain/wayan-claude-install/main/install.sh | sudo bash
```

Or from a clone:

```bash
sudo ./install.sh
```

The installer is **idempotent** — re-running it will not break an existing
install (env files and edited templates are preserved).

If you are reinstalling, clean up first:

```bash
sudo bash scripts/cleanup.sh
```

---

## 7. Authorize Claude Code

Claude Code is installed per-user for `wayan`. Log in once:

```bash
sudo -u wayan -i
claude        # follow the login flow, then exit
```

---

## 8. Telegram bot token — Jupiter

1. In Telegram, open **@BotFather** → `/newbot` → create the **Jupiter** bot.
2. Copy the token.
3. Put it in the env file:

```bash
sudoedit /etc/wayan-jupiter.env
# TELEGRAM_BOT_TOKEN=123456:ABC...
sudo systemctl restart wayan-jupiter.service
```

---

## 9. Telegram bot token — Uran

Use a **separate** bot so Uran stays an independent channel.

1. **@BotFather** → `/newbot` → create the **Uran** bot.
2. Copy the token.
3. Put it in the env file:

```bash
sudoedit /etc/wayan-uran.env
# TELEGRAM_BOT_TOKEN=987654:XYZ...
sudo systemctl restart wayan-uran.service
```

---

## 10. Verify

```bash
sudo bash scripts/healthcheck.sh
sudo bash tests/verify.sh

# live logs
journalctl -u wayan-jupiter.service -f
journalctl -u wayan-uran.service -f
```

---

## 11. Update

```bash
cd wayan-claude-install
sudo bash scripts/update.sh
```

Pulls the latest repo, re-runs the installer, restarts services, prints status.

---

## 12. Uninstall

Soft (keep user + home), so you can reinstall fresh:

```bash
sudo bash scripts/cleanup.sh
```

Full (removes workspaces, and the `wayan` user **only if** this installer
created it):

```bash
sudo bash scripts/uninstall.sh   # type DELETE to confirm
```

---

## 13. Voice input (Groq) — v1.1.0

Both agents accept Telegram **voice notes**. The flow:

```
voice note → getFile → download OGG/Opus → Groq Whisper → transcript → claude -p → text reply
```

The transcript is echoed back (📝 …) so you can confirm what was understood,
then it runs through the normal Claude flow. Text messages are unaffected.

**Enable it** by adding a Groq API key (from <https://console.groq.com>) to each
agent's env file:

```bash
sudoedit /etc/wayan-jupiter.env   # set GROQ_API_KEY=...
sudoedit /etc/wayan-uran.env      # set GROQ_API_KEY=...
sudo systemctl restart wayan-jupiter.service wayan-uran.service
```

Relevant env keys (defaults shown):

| Key | Default | Meaning |
| --- | --- | --- |
| `GROQ_API_KEY` | _(empty)_ | Groq key; blank disables voice |
| `VOICE_ENABLED` | `true` | Master voice switch |
| `VOICE_INPUT` | `true` | Accept incoming voice → transcription |
| `VOICE_OUTPUT` | `false` | TTS reply — **not implemented yet** |
| `GROQ_MODEL` | `whisper-large-v3-turbo` | Transcription model |
| `VOICE_TIMEOUT` | `120` | Seconds to wait for transcription |

No `ffmpeg` is required — Whisper accepts Telegram's OGG/Opus directly.

### File attachments (documents & photos)

Send a document or photo and the agent downloads it into
`<workspace>/uploads/` and passes Claude the saved path; the message **caption**
(if any) is used as the task. Photos use the largest available size.

| Key | Default | Meaning |
| --- | --- | --- |
| `FILES_ENABLED` | `true` | Accept document/photo attachments |
| `FILE_MAX_MB` | `20` | Reject larger files (Telegram caps bot downloads at 20 MB) |

**Returning files (outbox).** Anything Claude writes into `<workspace>/outbox/`
during a run is delivered back to you as a Telegram document — so you can upload
a task as a file and get the result back as a file. Only files created/modified
in that run are sent.

**Minimal storage.** Raw uploads are **temporary**: they land in
`<workspace>/uploads/tmp/`, get transcribed/analyzed into a **Markdown
transcript** in `<workspace>/transcripts/`, then the raw heavy file is deleted
(unless `FILE_KEEP_ORIGINAL=true`). A manual `scripts/cleanup-uploads.sh` sweeps
anything left in `uploads/tmp/` older than `FILE_RETENTION_HOURS` (default 24h).
Transcripts and all knowledge dirs are never swept. Full details:
[`docs/STORAGE_POLICY.md`](docs/STORAGE_POLICY.md).

## 14. Skills

Each agent workspace has a `skills/` directory of **read-only playbooks**
(`SKILL.md` files). When a task matches a skill, the agent reads that playbook
first and follows its output format.

| Skill | Purpose |
| --- | --- |
| `onchain-alpha` | Token / smart-money / flow / risk analysis |
| `content-engine` | TikTok / Reels / X content for Wayan Onchain |
| `file-analyst` | Analyze PDFs, screenshots, reports, contracts |
| `server-ops` | Read-only VPS diagnostics |
| `security-check` | Tokens, links, contracts, env, permissions |
| `agent-reviewer` | Review performance, propose improvements |

**Safety model — no self-editing.** Agents never edit `SKILL.md` or their own
`CLAUDE.md`. If a skill should change, the agent writes a **proposal** into
`skills/_proposals/` (skill, reason, observed problem, suggested diff, risk
level, rollback note) for a human to review. Nothing is auto-applied. Agents may
log notable success/failure patterns into `logs/successful` / `logs/failed`.

The installer copies `skills/` into both workspaces and **never overwrites**
skill files you've edited. See [`skills/README.md`](skills/README.md).

## 15. Day 2 Orchestration

On top of skills, each workspace has an `orchestration/` layer that keeps the
agents consistent, safe, and improvable **under your control** — they never
self-edit production instructions.

```
orchestration/
├── rules/       # hard rules (safety, skill-routing, services-map)
├── learnings/   # captured feedback → inbox → reviewed
├── memory/      # tiered context: hot / warm / cold
├── mapping/     # infrastructure, services, accounts (you customize)
└── skill-lab/   # experimental new-skill proposals
```

**New users get a ready template.** Customize these for your own project:

- `orchestration/mapping/infrastructure.md`
- `orchestration/mapping/services.md`
- `orchestration/mapping/accounts.example.md` → copy to `accounts.md` (git-ignored)
- `orchestration/memory/cold.md`
- `orchestration/rules/services-map.md`

**The manual learning loop:** you give feedback ("запомни…", "исправь…", "не
делай так…") → the agent records it in `learnings/inbox/` → on request it reviews
and **proposes** what should become a rule/skill/memory/mapping entry → you
approve → only then is it applied. **Auto-fix is disabled by default.** Full
guide: [`docs/DAY2_ORCHESTRATION.md`](docs/DAY2_ORCHESTRATION.md).

## 16. Troubleshooting

| Symptom | Check |
| --- | --- |
| `must run as root` | use `sudo` |
| `Unsupported Ubuntu` | only 22.04 / 24.04 are supported |
| Service won't start | `journalctl -u wayan-jupiter.service -e` |
| `claude: command not found` | log in once as `wayan` (section 7) |
| Telegram silent | token set in the right `.env`? service restarted? |
| Voice not transcribed | `GROQ_API_KEY` set? `VOICE_ENABLED`/`VOICE_INPUT=true`? service restarted? |
| sudoers error | `sudo visudo -cf /etc/sudoers.d/wayan-agents` |
| Need a clean slate | `sudo bash scripts/cleanup.sh` then reinstall |
