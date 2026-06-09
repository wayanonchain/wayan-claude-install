# Knowledge

Version-controlled snapshots of the agents' **approved** knowledge, exported
from the live VPS workspaces by [`scripts/export-knowledge.sh`](../scripts/export-knowledge.sh).

```
knowledge/
├── jupiter/
│   ├── memory/             # orchestration/memory (hot/warm/cold)
│   ├── rules/              # orchestration/rules
│   ├── skills/             # skills/*/SKILL.md
│   └── learnings-reviewed/ # orchestration/learnings/reviewed (approved only)
└── uran/
    └── (same structure)
```

## What this is (and isn't)

- **Is:** a reviewable, git-tracked copy of memory, rules, skills, and
  **reviewed** learnings — the knowledge that has already passed the human
  approval loop.
- **Is not:** a live sync. It is a deliberate, on-demand export you run and then
  review before committing.

## Never exported

The export is **whitelist-only**, so these are excluded by construction:
`uploads/`, `outbox/`, `.claude/`, env files (`/etc/wayan-*.env`),
`mapping/accounts.md`, and `learnings/inbox/` (un-reviewed). A secret scan also
aborts the export if any token/key pattern is found.

See [`docs/KNOWLEDGE_EXPORT.md`](../docs/KNOWLEDGE_EXPORT.md) for the full
storage → review → export → commit workflow.
