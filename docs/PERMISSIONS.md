# Agent Permissions — Role-Based Profiles

Jupiter and Uran run **headless** (`claude -p`, no TTY). Each agent has a
role-based permission profile at `<workspace>/.claude/settings.json` that decides
which tools run silently, which are blocked, and which files can never be edited.

> Scope: these profiles govern the **VPS agents only**. They are separate from
> your personal Claude Code settings on your own machine.

---

## How headless permissions behave (important)

In `claude -p` there is **no interactive prompt**, so the three lists resolve as:

| List | Headless effect |
| --- | --- |
| `allow` | runs **silently** |
| `ask` | **blocked** (nothing to prompt → denied; the agent reports it) |
| `deny` | **blocked**, overrides everything (incl. `acceptEdits`) |
| *(unlisted)* | **blocked** (default-deny without a TTY) |

So for the autonomous agents, `ask` ≈ `deny`: dangerous operations are simply
refused, and **you** perform them out-of-band. The `allow` list is what actually
enables a tool; `deny` is what hardens the protected files.

This is why MCP memory tools must be in `allow` — `--permission-mode acceptEdits`
only auto-accepts file edits, **not** MCP tools, so an un-listed `memory_store`
is denied.

---

## Jupiter — research / content agent

**Allowed (silent):**
- Read-only diagnostics: `systemctl status`, `journalctl`, `uptime`, `df`, `free`,
  `ps`, `ls`, `cat`, `find`, `grep`
- Research: `WebFetch`, `curl`, `python3`
- Git inspection: `git status`, `git diff`, `git log`
- File reads: `Read`
- OpenViking memory: `memory_health`, `memory_store`, `memory_recall`,
  `memory_forget`

**Gated (`ask` → blocked headless):** `git commit`, `git push`, `gh`, `ssh`,
`sudo`, `rm`, `chmod`, `chown`, `systemctl restart/stop/disable`,
`docker compose up/down/restart`, `apt`, `reboot`, `shutdown`.

## Uran — operations agent

Everything Jupiter has, **plus** safe ops:
- `docker compose ps` / `logs`, `docker compose restart openviking`
- `sudo systemctl restart|status wayan-jupiter.service` / `wayan-uran.service`
- `sudo journalctl -u wayan-jupiter.service` / `wayan-uran.service`

**Gated:** `git commit`/`push`, `gh`, `ssh`, `rm`, `chmod`, `chown`,
`systemctl stop/disable`, `docker compose down`, `apt`, `reboot`, `shutdown`,
`userdel`, `mkfs`, `dd`.

> **Why no broad `Bash(sudo:*)` in Uran's `ask`:** a broad `sudo:*` ask would
> shadow Uran's *specific* allowed `sudo systemctl restart wayan-*` commands and
> block them. Instead only the exact safe sudo commands are allowed; **all other
> sudo is default-denied** in headless mode.

---

## No-self-edit (enforced `deny`)

Both profiles **deny** `Edit`/`Write` to the agent's own production instructions —
so the agent can use them but never silently rewrite them:

```
CLAUDE.md, USER.md,
orchestration/rules/**, orchestration/memory/**, orchestration/mapping/**,
skills/**
```

`deny` overrides `acceptEdits`, so this holds even though the gateway runs in
`acceptEdits` mode. The agent can still write to its working areas
(`transcripts/`, `outbox/`, `learnings/inbox/`, `uploads/`).

---

## Deploy & update

- **Install (fresh):** `install.sh` copies `templates/<agent>/claude-settings.json`
  → `<workspace>/.claude/settings.json` **no-clobber** (never overwrites an
  edited one).
- **Update (explicit):** `scripts/apply-templates.sh` **backs up** any existing
  `settings.json` (`.bak.<timestamp>`) and applies the latest template.
- No restart needed — `claude -p` reads `.claude/settings.json` per invocation.
- These never touch env files, `ov.conf`, or any API keys.

## Changing a profile
Edit `templates/<agent>/claude-settings.json` in the repo, commit, then run
`scripts/apply-templates.sh` on the VPS to roll it out (with backups). To add a
new MCP tool, allow-list its exact identifier (e.g.
`mcp__plugin_openviking-memory_openviking-memory__memory_recall`).
