# Pack: devops — Developer / DevOps

Adapts the stock agents to a solo dev or small team running services. Markdown
overlay only — stock skills, with `server-ops` and `security-check` promoted,
plus a services-allowlist discipline seeded into rules and mapping.

- **Target user:** solo dev / small team operating servers.
- **Jupiter:** code, research, PR/diff summaries, incident write-ups.
- **Uran:** first-line SRE (health, logs, restarts within its permission profile).
- **Skills emphasized (all stock):** `server-ops`, `security-check`,
  `file-analyst`, `agent-reviewer`.

## What gets copied where

| Pack file | Destination (both workspaces unless noted) |
| --- | --- |
| `jupiter/PACK.md` | `<jupiter ws>/PACK.md` |
| `uran/PACK.md` | `<uran ws>/PACK.md` |
| `memory/cold.md` | `<ws>/orchestration/memory/cold.md` (seed, no-clobber) |
| `rules/devops-routing.md` | `<ws>/orchestration/rules/` |
| `mapping/devops-services.md` | `<ws>/orchestration/mapping/` |

## Install

```bash
WAYAN_PACK=devops sudo -E ./install.sh
```
