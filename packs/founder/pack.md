# Pack: founder — Founder / Startup Operator

Adapts the stock agents to an early-stage founder doing everything at once.
Markdown overlay only — stock skills, with `file-analyst` and `content-engine`
promoted, plus company-facts memory and an "investor-facing needs approval"
rule.

- **Target user:** early-stage founder / startup operator.
- **Jupiter:** analyst + writer (memos, research, decks narratives, interview
  notes).
- **Uran:** ops assistant (infra health, checklists, weekly digests).
- **Skills emphasized (all stock):** `file-analyst`, `content-engine`,
  `security-check`.

## What gets copied where

| Pack file | Destination (both workspaces unless noted) |
| --- | --- |
| `jupiter/PACK.md` | `<jupiter ws>/PACK.md` |
| `uran/PACK.md` | `<uran ws>/PACK.md` |
| `memory/cold.md` | `<ws>/orchestration/memory/cold.md` (seed, no-clobber) |
| `rules/founder-routing.md` | `<ws>/orchestration/rules/` |
| `mapping/founder-services.md` | `<ws>/orchestration/mapping/` |

## Install

```bash
WAYAN_PACK=founder sudo -E ./install.sh
```
