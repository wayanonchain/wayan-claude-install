# Infrastructure (customize this)

> Template. Replace placeholders with your real setup. No secrets — use
> placeholders like `<VPS_IP>` and keep real values out of git.

## Host
- Provider: _(fill in — e.g. VPS provider)_
- Host / IP: `<VPS_IP>`
- OS: Ubuntu 22.04 / 24.04
- Access: SSH as `root` (key-based)

## Users
- `wayan` — runs the agents (uid set by the installer)

## Key paths
- Workspaces: `/home/wayan/.claude-lab/{jupiter,uran}`
- Agent code + venv: `/opt/wayan-{jupiter,uran}`
- Env files: `/etc/wayan-{jupiter,uran}.env` (mode 0640, root:wayan)
- Sudoers: `/etc/sudoers.d/wayan-agents`

## Runtimes
- Node.js 22, Python 3, Claude Code (per-user `wayan`)

## Do not touch
- `wayan-bot.service`, `/opt/wayan_pirat_bot` (unrelated project)

_(Add networking, backups, DNS, and anything else specific to your host.)_
