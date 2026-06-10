# Public Template Guide — Fork & Make It Yours

This repo is a **public example/template**. You can fork it and adapt the agents
to your own project, server, and brand. This guide shows what to customize and —
importantly — **what to never commit**.

---

## 1. Fork the repo

On GitHub, click **Fork** on `wayanonchain/wayan-claude-install` to create your
own copy (e.g. `you/my-claude-agents`). Then clone it locally:

```bash
git clone https://github.com/YOU/my-claude-agents.git
cd my-claude-agents
```

Update the repo URL placeholders in `install.sh` and the scripts (search for
`wayanonchain/wayan-claude-install`) to point at **your** fork, so the VPS
installer pulls from your copy.

---

## 2. What to customize

| Path | What to change |
| --- | --- |
| `templates/jupiter/CLAUDE.md`, `templates/uran/CLAUDE.md` | The agents' role, voice, and rules for **your** project |
| `templates/*/USER.md` | Who the operator is, preferences, conventions |
| `templates/*/claude-settings.json` | Permission profiles (keep the safety `deny` rules) |
| `skills/` | Your own `SKILL.md` playbooks (rename/replace the Wayan ones) |
| `orchestration/mapping/infrastructure.md`, `services.md` | Your host, paths, services |
| `orchestration/mapping/accounts.example.md` | Copy to `accounts.md` (git-ignored) with your real handles |
| `orchestration/memory/cold.md` | Stable facts: who you are, your project, durable prefs |
| `orchestration/rules/services-map.md` | Which services your agents may manage |
| `README.md` | Your branding, project name, links |

Everything else (the gateway, installer mechanics, storage policy) works as-is.

---

## 3. What you must **NEVER** commit

These are secrets or runtime data. They are already in `.gitignore`, but double-
check before every push:

- **`*.env`** / env files — hold `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, etc.
- **`ov.conf`** — holds the **OpenAI key** and OpenViking server key.
- **Telegram bot tokens** (Jupiter + Uran).
- **Groq API keys.**
- **OpenAI API keys** (used by OpenViking).
- **Claude credentials** (`~/.claude/.credentials.json`, `.claude.json`).
- **`uploads/`** — raw user files (heavy, possibly private).
- **`transcripts/`** at the repo root — workspace transcripts (only curated
  Markdown under `knowledge/` is meant to be committed).
- **`orchestration/mapping/accounts.md`** — your real account map.
- **`~/.openviking/`**, `root_api_key`, user keys, SSH private keys.

> Rule of thumb: **if it's a key, token, credential, or a raw user file — it
> never goes in git.** Knowledge belongs in git as **Markdown**; secrets belong
> in `600`-permission files on the server.

### A quick safety check before pushing
```bash
git ls-files | grep -iE '\.env$|ov\.conf|credential|api[_-]?key|/uploads/|^transcripts/'
# should print NOTHING
```

---

## 4. Keep the safety model

When customizing, preserve these properties (they're what make the template
safe for beginners):

- **No self-editing:** agents can't rewrite `CLAUDE.md`/`rules`/`memory`/`skills`
  (enforced by `deny` rules — see [`PERMISSIONS.md`](PERMISSIONS.md)).
- **No autonomous auto-fix:** improvements go through human-reviewed proposals.
- **Minimal storage:** heavy uploads are temporary; knowledge is Markdown
  (see [`STORAGE_POLICY.md`](STORAGE_POLICY.md)).
- **Localhost-only memory:** OpenViking is never exposed publicly
  (see [`OPENVIKING_MEMORY.md`](OPENVIKING_MEMORY.md)).

---

## 5. Share responsibly

Your fork is public by default. Before sharing:
- Confirm no secrets were ever committed (check the **full history**, not just
  the latest commit — a leaked key in an old commit is still leaked).
- Keep `accounts.example.md` as placeholders only.
- Point newcomers at [`COSTS_AND_SERVICES.md`](COSTS_AND_SERVICES.md) and
  [`TERMS_GLOSSARY.md`](TERMS_GLOSSARY.md).
