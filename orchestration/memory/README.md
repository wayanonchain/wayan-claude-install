# Memory

Tiered context the agent can consult. Memory is **read-first**: the agent reads
it to stay consistent, but does **not** write to it without user approval.

| Tier | File | Holds | Volatility |
| --- | --- | --- | --- |
| Hot | `hot.md` | Active focus right now — current goals, what's in flight | changes often |
| Warm | `warm.md` | Recent context — last weeks, recurring threads | changes weekly |
| Cold | `cold.md` | Stable facts — who the operator is, long-standing preferences | rarely changes |

## How to use

- Before an important task, skim `hot.md`, then `warm.md`, then `cold.md` as
  needed for relevant context.
- Promote/demote between tiers only via the manual learning loop (propose →
  approve → apply). The agent never silently rewrites memory.

## Customize

- `cold.md` is the one new users should fill in first (who you are, project,
  durable preferences).
- Keep secrets out of memory — those belong in `mapping/accounts.md` (untracked).
