# Creator Pack — Routing & Hard Rules

Extends `rules/skill-routing.md` for the creator pack. Stock skills only; the
base routing table stays valid.

## Pack routing

| Task cue | Skill chain |
| --- | --- |
| script / hook / caption / thread / post | `skills/content-engine/SKILL.md` |
| uploaded video or audio → content | `skills/file-analyst/SKILL.md` → `content-engine` |
| analytics export / screenshot | `skills/file-analyst/SKILL.md` |
| sponsor link / suspicious DM | `skills/security-check/SKILL.md` |

## Hard rules

1. **Brand voice is law.** Every draft conforms to the voice section of
   `memory/cold.md`. If voice is not filled in yet, ask before drafting.
2. **Drafts, not posts.** The agent never publishes and never claims it did.
   Platform automation stays within each platform's ToS — manual publish only.
3. **Respect copyright.** Repurposing covers the operator's own content;
   third-party material needs the operator's explicit confirmation of rights.
4. **No invented metrics.** Performance claims come from operator-provided
   exports/screenshots only, dated.
