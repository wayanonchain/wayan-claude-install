# Skill Improvement Proposals

This is how agents suggest changes to **read-only** production skills.

> Agents MUST NOT edit any `SKILL.md` or `CLAUDE.md` directly. To improve a
> skill, drop a proposal file here. A human reviews and applies (or rejects) it.
> **Nothing in this folder is ever auto-applied.**

## Filename

```
YYYY-MM-DD-<skill-name>-<short-slug>.md
```

Example: `2026-06-08-onchain-alpha-add-liquidity-check.md`

## Required fields

Every proposal must include all of these:

- **Skill** — the skill name being changed
- **Reason for change** — why this change is worth making
- **Observed problem** — the concrete problem you hit (with context)
- **Suggested diff** — the proposed edit, ideally as a fenced ` ```diff ` block
- **Risk level** — `low` | `medium` | `high`
- **Rollback note** — how to revert if the change is wrong

## Template

Copy this into a new file and fill it in:

```markdown
# Proposal: <short title>

- **Skill:** <skill-name>
- **Risk level:** low | medium | high

## Reason for change
<why>

## Observed problem
<what went wrong, with concrete context>

## Suggested diff
​```diff
- old line
+ new line
​```

## Rollback note
<how to revert this change safely>
```

## Review workflow

1. Agent writes a proposal here (never edits the skill).
2. Human reads it, checks the diff and risk level.
3. Human applies it to the real `SKILL.md` (or rejects it) and commits.
4. Optionally, the proposal file is moved to an `applied/` or `rejected/` note.
