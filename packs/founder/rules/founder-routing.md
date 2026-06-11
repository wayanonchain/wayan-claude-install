# Founder Pack — Routing & Hard Rules

Extends `rules/skill-routing.md` for the founder pack. Stock skills only; the
base routing table stays valid.

## Pack routing

| Task cue | Skill chain |
| --- | --- |
| call recording / interview audio | transcript → `skills/file-analyst/SKILL.md` |
| contract / deck / report upload | `skills/file-analyst/SKILL.md` |
| memo / one-pager / pitch narrative / digest | `skills/content-engine/SKILL.md` |
| vendor, tool, or link diligence | `skills/security-check/SKILL.md` |

## Hard rules

1. **Investor-facing = approval-gated.** Memos, decks, emails to investors are
   always `DRAFT` until the operator explicitly approves. The agent never
   sends anything anywhere itself.
2. **Source every market number.** TAM/SAM, growth rates, competitor metrics —
   cite the source or mark the number as an assumption. Never fill gaps with
   plausible figures.
3. **Confidential-data hygiene.** Raw recordings/contracts follow minimal
   storage (temporary uploads, durable distilled notes). Nothing confidential
   goes into git or public drafts.
4. **Facts vs. narrative.** Company facts come from `memory/cold.md`; if the
   narrative needs a fact that isn't there, ask — don't improvise it.
