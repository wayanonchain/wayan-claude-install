# DevOps Pack — Routing & Hard Rules

Extends `rules/skill-routing.md` for the devops pack. Stock skills only; the
base routing table stays valid.

## Pack routing

| Task cue | Skill chain |
| --- | --- |
| service down / slow / errors / health | `skills/server-ops/SKILL.md` |
| CI log / stack trace / diff as a file | `skills/file-analyst/SKILL.md` → `server-ops` |
| dependency, link, config, exposure question | `skills/security-check/SKILL.md` |
| reviewing how the agents handled an incident | `skills/agent-reviewer/SKILL.md` |

## Hard rules

1. **Strict service allowlist.** Only services listed under "Managed" in
   `mapping/devops-services.md` may be restarted, and only by Uran within its
   sudoers grants. Everything else: diagnose + hand the operator the command.
2. **Diagnose → state cause → act.** Never restart blind; never "fix" by
   rebooting.
3. **Secrets never leave logs.** No env values, tokens, or key material in
   Telegram replies or write-ups — name the variable, never its value.
4. **Destructive ops are operator-only:** stop/disable, package upgrades,
   firewall, user management, deletes. Propose, don't perform.
5. **Every incident gets a write-up** (symptom → cause → fix → prevention) in
   `logs/` so it becomes a learning.
