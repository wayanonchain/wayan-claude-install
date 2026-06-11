# DevOps Pack — Services Map (customize this — this is the allowlist)

> The authoritative allowlist of what the agents may touch. Keep it tight.
> No secrets here.

## Managed (restart allowed, within Uran's sudoers grants)

| Service | Role | Allowed actions |
| --- | --- | --- |
| `wayan-jupiter.service` | Main agent (Telegram gateway) | status, restart |
| `wayan-uran.service` | Backup agent | status, restart |
| _(add your own services + extend sudoers deliberately)_ | | |

## Observed (read-only: status + journal, never restart)

| Service | Note |
| --- | --- |
| _(fill in: nginx, postgres, docker, …)_ | diagnose only, propose commands |

## Off-limits (do not touch, do not stop, do not edit)

| Service / path | Note |
| --- | --- |
| _(fill in anything unrelated running on the host)_ | |

## External tooling

| Tool | Use |
| --- | --- |
| GitHub / `gh` | repos, PRs, CI logs (read) |
| CI provider | _(fill in)_ |

## Rules

- A service not listed here is **off-limits by default**.
- Extending the "Managed" list means also extending the sudoers file —
  operator-only change.
