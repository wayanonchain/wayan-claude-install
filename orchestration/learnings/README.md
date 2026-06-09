# Learnings

Captured user feedback that may (after review and approval) become a rule,
skill, memory entry, or mapping update.

```
learnings/
├── inbox/      # raw feedback the agent just captured
└── reviewed/   # feedback that has been triaged into a proposal
```

## How it works

1. **Capture.** When the user gives feedback — e.g. "запомни…", "исправь…",
   "не делай так…" — the agent writes one file into `inbox/`.
2. **Review.** Periodically (or when asked), the agent reads `inbox/` and
   **proposes** what each item should become:
   - a **rule** (`orchestration/rules/`)
   - a **skill** change (`skills/_proposals/`)
   - a **memory** entry (`orchestration/memory/`)
   - a **mapping** update (`orchestration/mapping/`)
3. **Approve.** The user approves (or rejects) each proposal.
4. **Apply + archive.** Only after approval, a human applies the change and the
   learning file is moved to `reviewed/`.

## Inbox file format

Filename: `YYYY-MM-DD-<short-slug>.md`

```markdown
- **Date:** YYYY-MM-DD
- **Feedback (verbatim):** "<exactly what the user said>"
- **Context:** <what task this came from>
- **Candidate target:** rule | skill | memory | mapping (agent's guess)
- **Status:** new
```

## Rules
- The agent may **write to `inbox/`** freely (that is just capturing feedback).
- The agent must **not** edit `rules/`, `memory/`, `skills/`, etc. from a
  learning without explicit user approval.
