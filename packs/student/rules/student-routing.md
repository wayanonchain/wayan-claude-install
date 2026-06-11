# Student Pack — Routing & Hard Rules

Extends `rules/skill-routing.md` for the student pack. Stock skills only; the
base routing table stays valid.

## Pack routing

| Task cue | Skill chain |
| --- | --- |
| PDF / paper / screenshot / book chapter | `skills/file-analyst/SKILL.md` |
| lecture or voice recording | transcript → `file-analyst` summary shape |
| flashcards / explainer / study post | `file-analyst` → `skills/content-engine/SKILL.md` |
| "review how my notes are going" | `skills/agent-reviewer/SKILL.md` |

## Hard rules

1. **Source + locator for every claim.** Title, author, and page (or
   timestamp). If a source is unknown, say "unknown source" — never invent one.
2. **Quote vs. paraphrase is always explicit.** Quotation marks + locator for
   quotes; everything else is clearly the agent's wording.
3. **Plagiarism guardrail.** If asked for text to submit as the operator's own
   work, deliver study material and flag the academic-integrity risk once.
4. **Paywalled content:** work only with what the operator lawfully provides;
   never attempt to bypass access controls.
5. **The library is sacred.** `transcripts/` and notes are never deleted or
   rewritten in bulk without explicit operator approval.
