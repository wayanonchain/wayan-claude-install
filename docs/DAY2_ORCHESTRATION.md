# Day 2 Orchestration — Guide

This guide explains the orchestration layer for newcomers: what each part is,
why the agent never "fixes itself" automatically, and how to teach it safely.

If Day 1 was "two agents that talk to Telegram and run Claude," Day 2 is "those
agents stay consistent, safe, and improvable over time — under your control."

---

## The pieces

### `CLAUDE.md` — the agent's constitution
The top-level instructions Claude reads on **every** task in a workspace. It
defines the agent's role, the skills routing, the file-exchange convention, and
the Day 2 orchestration checklist. **The agent must never edit this on its own.**

### `orchestration/rules/` — hard rules
Non-negotiable constraints (`safety.md`), skill routing (`skill-routing.md`),
and which services may be managed (`services-map.md`). Rules outrank
convenience. Production rules change only with your approval.

### `orchestration/learnings/` — captured feedback
When you say "запомни…", "исправь…", "не делай так…", the agent writes the
feedback into `learnings/inbox/`. Later it reviews the inbox and **proposes**
what should become a rule/skill/memory/mapping entry. Approved items move to
`learnings/reviewed/`.

### `orchestration/memory/` — tiered context
- `hot.md` — what's in flight right now
- `warm.md` — recent recurring context
- `cold.md` — stable facts (who you are, durable preferences)

The agent **reads** memory to stay consistent; it updates memory only with your
approval.

### `orchestration/mapping/` — the world map
`infrastructure.md` (hosts/paths), `services.md` (systemd services),
`accounts.example.md` (shape of accounts — copy to `accounts.md`, never commit
secrets). Consult these when a task involves infrastructure, services, accounts,
GitHub, VPS, Telegram, Groq, or external tools.

### `orchestration/skill-lab/` — experimental skills
A staging area for **new** skill ideas (`proposals/`). Nothing here is active;
promotion into `skills/` is a deliberate, approved step.

### `uploads/tmp/` + `transcripts/` — minimal storage
Heavy uploads are temporary (`uploads/tmp/`), turned into Markdown
(`transcripts/`), then deleted. Knowledge is text, not raw media. This is the
same "knowledge lives in files, as Markdown" principle applied to user uploads.
See [`STORAGE_POLICY.md`](STORAGE_POLICY.md).

---

## Why auto-fix is disabled by default

An agent that silently rewrites its own rules, memory, or skills is an agent you
can't trust or audit. So by design:

- The agent **never** edits `CLAUDE.md`, `USER.md`, `rules/`, `memory/`, or
  `SKILL.md` without your explicit approval.
- Improvements are written as **proposals**; you apply them.
- This keeps a human in the loop and every change reviewable in git.

Autonomous auto-fix may arrive later as an **opt-in** feature — off by default.

---

## How to teach the agent safely (the learning loop)

1. **You give feedback** in plain language.
2. **Agent captures it** into `learnings/inbox/` (this is just note-taking —
   always allowed).
3. **Agent reviews** the inbox when you ask and proposes what each item should
   become: a rule, a skill change, a memory entry, or a mapping update.
4. **You approve** (or reject).
5. **Only after approval** does a change land in `rules/` / `memory/` / etc., and
   the learning moves to `learnings/reviewed/`.

The agent never skips step 4.

---

## Using the Wayan template for your own project

The repo ships a ready, public-safe template. To make it yours:

1. Fill in `memory/cold.md` — who you are, your project, durable preferences.
2. Fill in `mapping/infrastructure.md` and `mapping/services.md` for your host.
3. Copy `mapping/accounts.example.md` → `mapping/accounts.md` and add real
   handles. `accounts.md` is git-ignored — keep secrets out of git.
4. Adjust `rules/services-map.md` to your services.
5. Add project-specific rules to `rules/` (with your approval) as you go.

Everything else (skills, gateway, installer) keeps working unchanged.

---

## Example commands to give the agent

**Example 1 — capture a preference**
> "Запомни: в моих постах не используй длинные тире."

→ The agent writes a file into `learnings/inbox/` recording the feedback. It does
**not** edit any rule yet.

**Example 2 — review and propose**
> "Разбери learnings за неделю и предложи, что перенести в rules."

→ The agent reads `learnings/inbox/`, groups the items, and produces a
**proposal** of which should become rules/skills/memory/mapping. Nothing is
applied yet.

**Example 3 — apply after approval**
> "Добавь это правило в rules после моего подтверждения."

→ The agent shows the exact change and waits. **Only after you confirm** does it
apply the rule (a human-approved edit) and move the learning to `reviewed/`.

---

## Quick reference: the Day 2 checklist (also in `CLAUDE.md`)

Before important tasks the agent should:
1. Read `CLAUDE.md` principles.
2. Check `orchestration/rules/` for hard rules.
3. Check `orchestration/mapping/` for infra/services/accounts/external tools.
4. Check `orchestration/memory/` for relevant context.
5. Use `skills/` when a task matches a skill (chain when needed).
6. Record "запомни/исправь/не делай так" feedback into `learnings/inbox/`.
7. Never apply self-fixes automatically.
8. Propose improvements as proposal files only.
9. Never edit production rules/skills/memory/CLAUDE.md/USER.md without approval.
