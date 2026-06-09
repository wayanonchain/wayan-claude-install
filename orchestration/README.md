# Wayan Orchestration (Day 2)

The orchestration layer is how the agents stay consistent, safe, and improvable
over time — **without ever editing their own production instructions on their
own**. It sits alongside `skills/` in each agent workspace.

```
orchestration/
├── rules/       # hard rules the agent must follow (safety, routing, services)
├── learnings/   # captured user feedback → inbox, then reviewed
├── memory/      # tiered context: hot / warm / cold
├── mapping/     # infrastructure, services, accounts (you customize these)
└── skill-lab/   # experimental skill ideas as proposals
```

## Core safety model

- **No autonomous auto-fix.** The agent never silently changes its own behavior.
- **No self-editing of production files.** The agent must not modify
  `CLAUDE.md`, `USER.md`, any `rules/`, `memory/`, or `skills/SKILL.md` without
  **explicit user approval**.
- **Proposals, not mutations.** Improvements are written as proposal files
  (`skill-lab/proposals/`, `skills/_proposals/`) for a human to apply.
- **No external API dependencies.** This layer is plain Markdown.

## The manual learning loop

1. User gives feedback ("запомни…", "исправь…", "не делай так…").
2. Agent records it in `learnings/inbox/`.
3. Periodically, the agent reviews `learnings/inbox/` and **proposes** what
   should become a rule / skill / memory / mapping entry.
4. User approves.
5. **Only after approval** are `rules/`, `memory/`, etc. updated, and the
   learning is moved to `learnings/reviewed/`.

## What you must customize

The repo ships a ready template. For your own project, fill in:

- `mapping/infrastructure.md`
- `mapping/services.md`
- `mapping/accounts.example.md` (copy to `accounts.md`, keep secrets out of git)
- `memory/cold.md`
- `rules/services-map.md`

See [`docs/DAY2_ORCHESTRATION.md`](../docs/DAY2_ORCHESTRATION.md) for the full guide.
