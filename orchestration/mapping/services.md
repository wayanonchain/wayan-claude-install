# Services (customize this)

> systemd services on the host and how the agent may interact with them.
> Keep in sync with `rules/services-map.md`.

## Managed (Wayan agents)

| Service | Role | Entrypoint | Allowed actions |
| --- | --- | --- | --- |
| `wayan-jupiter.service` | Main agent (Telegram gateway) | `/opt/wayan-jupiter/venv/bin/python -m gateway` | status, restart |
| `wayan-uran.service` | Backup / root-fix agent | `/opt/wayan-uran/venv/bin/python -m gateway` | status, restart |

- Both run as `wayan`, read config from `/etc/wayan-<agent>.env`.
- Uran has scoped sudo to restart these and read their journals.

## Off-limits

| Service / path | Note |
| --- | --- |
| `wayan-bot.service` | Unrelated project — do not stop/disable/edit |
| `/opt/wayan_pirat_bot` | Unrelated project data |

## Customize
- Add your own services, their entrypoints, and what the agent may do with them.
