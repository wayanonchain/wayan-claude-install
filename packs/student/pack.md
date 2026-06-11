# Pack: student — Researcher / Student

Adapts the stock agents to a grad student, analyst, or lifelong learner.
Markdown overlay only — stock skills, with `file-analyst` promoted to the
front, plus citation discipline and a topic-map memory seed.

- **Target user:** student, researcher, analyst.
- **Jupiter:** reading, summarizing, organizing knowledge (PDFs, lectures,
  voice notes → structured Markdown).
- **Uran:** library ops (workspace/vault structure, pipeline health).
- **Skills emphasized (all stock):** `file-analyst`, `content-engine` (for
  study notes/explainers), `agent-reviewer`.

## What gets copied where

| Pack file | Destination (both workspaces unless noted) |
| --- | --- |
| `jupiter/PACK.md` | `<jupiter ws>/PACK.md` |
| `uran/PACK.md` | `<uran ws>/PACK.md` |
| `memory/cold.md` | `<ws>/orchestration/memory/cold.md` (seed, no-clobber) |
| `rules/student-routing.md` | `<ws>/orchestration/rules/` |
| `mapping/student-services.md` | `<ws>/orchestration/mapping/` |

## Install

```bash
WAYAN_PACK=student sudo -E ./install.sh
```
