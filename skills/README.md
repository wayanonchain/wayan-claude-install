# Wayan Skills

Skills are **read-only operational playbooks** for the Wayan agents (Jupiter and
Uran). Each skill is a `SKILL.md` describing when to use it, how to think about
the task, and the exact output format to produce.

## Principles

- **Read-only in production.** Agents use skills to do work; they do **not**
  edit `SKILL.md` (or `CLAUDE.md`) themselves. No agent mutates its own
  production instructions.
- **Proposals, not self-editing.** If an agent finds a way to improve a skill,
  it writes a proposal into [`_proposals/`](_proposals/README.md). A human
  reviews and applies it. Nothing is auto-applied.
- **No external API calls** from skills unless explicitly configured later.
- **No new runtime dependencies.** Skills are plain Markdown; they add nothing
  to the gateway's Python dependencies.

## How agents use skills

1. When a task matches a skill, read that skill's `SKILL.md` **first**.
2. Follow it as a playbook and produce the specified output format.
3. If something is missing or wrong, create a proposal in `_proposals/`.
4. Optionally log a notable success/failure pattern into `../logs/`.

## Available skills

| Skill | Purpose |
| --- | --- |
| [`onchain-alpha`](onchain-alpha/SKILL.md) | Token / smart-money / flow / risk analysis |
| [`content-engine`](content-engine/SKILL.md) | TikTok / Reels / X content for Wayan Onchain |
| [`file-analyst`](file-analyst/SKILL.md) | Analyze PDFs, screenshots, reports, contracts |
| [`server-ops`](server-ops/SKILL.md) | Read-only VPS diagnostics |
| [`security-check`](security-check/SKILL.md) | Tokens, links, contracts, env, permissions |
| [`agent-reviewer`](agent-reviewer/SKILL.md) | Review agent performance, propose improvements |

## Layout

```
skills/
├── <skill>/SKILL.md   # one playbook per skill (read-only)
├── _proposals/        # agent-written improvement proposals (human-reviewed)
└── README.md          # this file
```

On the VPS, this tree is copied into each agent's workspace
(`/home/wayan/.claude-lab/<agent>/skills`). The installer **never overwrites**
skill files you have edited.
