# Agent Pattern Logs

A lightweight, append-only record of **notable** outcomes the agents choose to
remember — to inform later reviews (see the `agent-reviewer` skill).

```
logs/
├── successful/   # patterns that worked well
└── failed/       # patterns that went wrong
```

## When to log

Only when it's genuinely useful — a reusable approach that worked, or a failure
worth not repeating. This is not a transcript of every message.

## How to log

Write a small Markdown file per notable case:

```
<successful|failed>/YYYY-MM-DD-<short-slug>.md
```

Suggested contents:

- **What the task was**
- **What approach was used**
- **Outcome** (and why it worked / failed)
- **Takeaway** (what to do next time)

## Rules

- These are notes, not instructions. They never override `CLAUDE.md` or skills.
- If a pattern suggests a skill should change, that goes through a **proposal**
  in `skills/_proposals/` — not a direct edit.
- On the VPS these live per-agent at
  `/home/wayan/.claude-lab/<agent>/logs/{successful,failed}`.
