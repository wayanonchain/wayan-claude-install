# Pack: onchain — Crypto / Onchain Analyst

The original Wayan profile, formalized as a pack. The stock install is already
tuned for onchain research (skills `onchain-alpha`, `security-check`,
`content-engine`), so this pack is a **thin overlay**: it makes the role
explicit, seeds the memory structure for watchlists and theses, and pins the
hard rules that were previously implicit.

- **Target user:** trader, analyst, alpha-channel owner.
- **Jupiter:** onchain research + content from research.
- **Uran:** ops + data-pipeline health.
- **Skills emphasized (all stock):** `onchain-alpha`, `security-check`,
  `content-engine`, `file-analyst`.

## What gets copied where

| Pack file | Destination (both workspaces unless noted) |
| --- | --- |
| `jupiter/PACK.md` | `<jupiter ws>/PACK.md` |
| `uran/PACK.md` | `<uran ws>/PACK.md` |
| `memory/cold.md` | `<ws>/orchestration/memory/cold.md` (seed, no-clobber) |
| `rules/onchain-routing.md` | `<ws>/orchestration/rules/` |
| `mapping/onchain-services.md` | `<ws>/orchestration/mapping/` |

## Install

```bash
WAYAN_PACK=onchain sudo -E ./install.sh
```
