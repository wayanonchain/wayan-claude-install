# Knowledge Export — Guide

How the agents' knowledge is **stored**, **reviewed**, **exported**, and
**committed** — safely, with a human in the loop at every gate.

The principle: research and file preparation can be autonomous, but **publishing
knowledge to git is always a deliberate, reviewed step.**

---

## 1. Where knowledge lives (on the VPS)

Each agent has a workspace at `/home/wayan/.claude-lab/<agent>/`. The knowledge
worth version-controlling lives in four places:

| Source (per agent) | What it is |
| --- | --- |
| `orchestration/memory/` | Tiered context: `hot.md`, `warm.md`, `cold.md` |
| `orchestration/rules/` | Hard rules (safety, skill-routing, services-map) |
| `skills/` | Read-only `SKILL.md` playbooks |
| `orchestration/learnings/reviewed/` | Feedback that has been **approved** |

Everything else in the workspace is **not** knowledge to export — see §4.

---

## 2. How knowledge is reviewed (before it can be exported)

Knowledge only becomes "approved" through the manual learning loop
(see [`DAY2_ORCHESTRATION.md`](DAY2_ORCHESTRATION.md)):

1. User gives feedback → agent records it in `learnings/inbox/`.
2. Agent reviews the inbox and **proposes** rule/skill/memory/mapping changes.
3. **User approves.**
4. A human applies the change and moves the item to `learnings/reviewed/`.

So by the time something is in `rules/`, `memory/`, `skills/`, or
`learnings/reviewed/`, it has already passed human review. The export only ever
pulls from those approved locations.

---

## 3. How export works

Run from the repo root:

```bash
bash scripts/export-knowledge.sh
# or target a different host:
WAYAN_VPS=root@1.2.3.4 bash scripts/export-knowledge.sh
```

The script:

1. Connects to the VPS over SSH (you'll be prompted to approve the SSH — by
   design; SSH is gated).
2. Streams **only** the four whitelisted directories per agent (via `tar` over
   SSH — no rsync dependency).
3. Runs a **secret scan** on every pulled tree. If anything matching a token/key
   pattern is found (`TELEGRAM_BOT_TOKEN=…`, `GROQ_API_KEY=…`, `gsk_…`, bot-token
   shapes, AWS keys, private-key headers), it **aborts before writing anything**
   and shows the location with the value redacted.
4. Mirrors each directory into `knowledge/<agent>/<name>/`.
5. Shows `git status` + `git diff` for `knowledge/` and **stops**.

It does **not** `git add`, `commit`, or `push`. Ever.

Destination layout:

```
knowledge/jupiter/{memory,rules,skills,learnings-reviewed}/
knowledge/uran/{memory,rules,skills,learnings-reviewed}/
```

---

## 4. What is never exported

The export is **whitelist-based**, so these are excluded by construction (not by
a fragile blacklist):

- `uploads/` — user-sent files
- `outbox/` — generated deliverables
- `.claude/` — Claude Code internal state / credentials
- env files — `/etc/wayan-*.env` (tokens live here, referenced by name only)
- `mapping/accounts.md` — real account map (also git-ignored)
- `learnings/inbox/` — raw, **un-reviewed** feedback

The secret scan is a second line of defence in case a secret was pasted into an
otherwise-approved file (e.g. someone put a token in `memory/cold.md`).

---

## 5. How knowledge is committed (the publish step)

Publishing is manual and gated (git commit/push require approval in this setup):

```bash
# 1. Review the diff the script printed.
git add knowledge/
git commit -m "knowledge: export from VPS (<date>)"
git push
```

Only do this after reading the diff. If the diff contains anything unexpected,
do not commit — investigate on the VPS first.

---

## 6. Why it's structured this way

- **Whitelist, not blacklist** — you can't accidentally leak `uploads/` or
  `.claude/` because they're never in scope.
- **Secret scan** — defence in depth against a stray token.
- **Show-diff-only** — nothing is published without your eyes on the change.
- **No autonomous git** — `commit`/`push` are deliberately outside the autonomy
  envelope, matching the "research yes, publishing no" permission strategy.
