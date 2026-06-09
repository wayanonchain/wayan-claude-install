# Skill Routing Rules

How to pick and combine skills. This mirrors the `## Skills Usage` section of
`CLAUDE.md` and is the authoritative reference.

## Routing table

| Task cue | Skill |
| --- | --- |
| onchain / token / project research | `skills/onchain-alpha/SKILL.md` |
| TikTok / Reels / X / content | `skills/content-engine/SKILL.md` |
| uploaded file / PDF / screenshot / contract / report | `skills/file-analyst/SKILL.md` |
| VPS / systemctl / journalctl / server diagnostics | `skills/server-ops/SKILL.md` |
| suspicious link / contract / env / permissions / security | `skills/security-check/SKILL.md` |
| improving agent behavior / skills / reviews | `skills/agent-reviewer/SKILL.md` |

## Chaining

- A task may match **multiple** skills. Read **all** relevant `SKILL.md` first,
  then apply them in logical order. Do not stop at the first match.
- Example: "analyze an uploaded token report and write an X post" →
  `file-analyst` → `onchain-alpha` → `content-engine`.

## Rules

- Use skills as operational playbooks; follow their output format.
- Do not modify `SKILL.md` directly. Improvements go to `skills/_proposals/`.
- Never auto-apply a proposal.
