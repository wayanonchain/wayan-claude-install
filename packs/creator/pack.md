# Pack: creator — Content Creator / Influencer

Adapts the stock agents to a solo creator running TikTok / Reels / X / YouTube.
Markdown overlay only — stock skills, with `content-engine` and `file-analyst`
promoted to the front, plus a brand-voice memory seed.

- **Target user:** solo creator, influencer.
- **Jupiter:** scriptwriter + repurposer (idea → scripts, long video → clips).
- **Uran:** publishing-pipeline ops (gateway health, upload/transcription flow).
- **Skills emphasized (all stock):** `content-engine`, `file-analyst`.

## What gets copied where

| Pack file | Destination (both workspaces unless noted) |
| --- | --- |
| `jupiter/PACK.md` | `<jupiter ws>/PACK.md` |
| `uran/PACK.md` | `<uran ws>/PACK.md` |
| `memory/cold.md` | `<ws>/orchestration/memory/cold.md` (seed, no-clobber) |
| `rules/creator-routing.md` | `<ws>/orchestration/rules/` |
| `mapping/creator-services.md` | `<ws>/orchestration/mapping/` |

## Install

```bash
WAYAN_PACK=creator sudo -E ./install.sh
```
