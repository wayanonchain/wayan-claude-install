# Services Map (customize this)

Which services the agent may manage, and how. **This is a template — adjust it
to your host.** Keep it in sync with `mapping/services.md`.

## Wayan agent services (managed)

| Service | Role | Allowed actions |
| --- | --- | --- |
| `wayan-jupiter.service` | Main agent | status, restart (via scoped sudo) |
| `wayan-uran.service` | Backup / root-fix agent | status, restart (via scoped sudo) |

Uran has scoped sudo (see `/etc/sudoers.d/wayan-agents`) to restart these and
read their journals. That is the limit of its privilege by default.

## Do NOT touch

| Service / path | Reason |
| --- | --- |
| `wayan-bot.service` | Unrelated project — never stop/disable/edit |
| `/opt/wayan_pirat_bot` | Unrelated project data |

## Customize

- Add your own services here with their allowed actions.
- Anything not listed as "managed" is read-only unless the user approves.
