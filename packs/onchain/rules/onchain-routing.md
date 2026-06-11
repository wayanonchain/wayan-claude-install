# Onchain Pack — Routing & Hard Rules

Extends `rules/skill-routing.md` for the onchain pack. Stock skills only; the
base routing table stays valid.

## Pack routing

| Task cue | Skill chain |
| --- | --- |
| token / project / wallet / flow research | `skills/onchain-alpha/SKILL.md` |
| contract address or link of unknown origin | `skills/security-check/SKILL.md` → `onchain-alpha` |
| research → post / thread / short | `onchain-alpha` → `skills/content-engine/SKILL.md` |
| tokenomics PDF / chart screenshot / report | `skills/file-analyst/SKILL.md` → `onchain-alpha` |

## Hard rules

1. **Never invent numbers.** Every figure (mcap, holders, flows, dates) must
   come from a source listed in `mapping/onchain-services.md`, cited inline.
2. **Date everything.** Onchain data is only valid with an as-of timestamp.
3. **Verdict format is fixed:** `watch / avoid / deep dive`, with 1–3 reasons.
4. **NFA framing** on anything that could be published. No buy/sell calls.
5. **Security first.** Unknown contracts/links go through `security-check`
   before any other analysis. Never connect to, sign, or simulate transactions.
