# Rules

Hard rules the agent must follow. Rules outrank convenience: if a rule conflicts
with what would be easier, the rule wins.

| File | What it governs |
| --- | --- |
| `safety.md` | Non-negotiable safety constraints |
| `skill-routing.md` | When to read which skill, and how to chain skills |
| `services-map.md` | Which services exist and how they may be managed (customize) |

## Editing rules

- Rules are **production files**. The agent must **not** edit them on its own.
- Changes happen only via the manual learning loop: a proposal, then explicit
  user approval, then a human applies the change.
- Keep each rule short, testable, and unambiguous.
