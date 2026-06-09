# Skill Lab

A staging area for **experimental** skill ideas — new skills or larger reworks
that aren't ready to touch production `skills/`.

```
skill-lab/
└── proposals/   # draft skill ideas (human-reviewed, never auto-applied)
```

## How it works

- The agent may draft a new-skill idea here as a proposal.
- Nothing in `skill-lab/` is active — agents do **not** route tasks to it.
- A human reviews a proposal and, if good, promotes it into a real
  `skills/<name>/SKILL.md` (a deliberate, approved action).

## Difference from `skills/_proposals/`

- `skills/_proposals/` — proposed **edits to existing** skills.
- `skill-lab/proposals/` — proposed **new** skills or experimental reworks.

## Proposal format

Filename: `YYYY-MM-DD-<skill-name>.md`

```markdown
# Skill idea: <name>

- **Purpose:** <what it does>
- **When to use:** <routing cues>
- **Output format:** <the structured output>
- **Risk / notes:** <anything to watch>
- **Status:** draft
```

Nothing here is auto-applied. Promotion to `skills/` requires explicit approval.
