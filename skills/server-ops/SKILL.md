---
name: server-ops
description: Read-only VPS diagnostics and operational checks. No destructive commands without explicit approval.
read_only: true
---

# Server Ops

## Purpose
Diagnose the health of the VPS and the Wayan services using **read-only**
commands. Primarily Uran's playbook, but available to both agents.

## When to use
- "Is the server OK?", "why is Jupiter down?", "check disk/memory/logs".
- Triaging a failed or misbehaving service.

## Allowed focus (read-only)
- `systemctl status <unit>` — service state
- `journalctl -u <unit>` — service logs
- `df -h` — disk usage
- `free -m` — memory
- `ps aux` — processes
- `uptime` — load / uptime

## How to think
- Start broad (uptime, df, free), then narrow to the failing unit's logs.
- Report findings as evidence → likely cause → recommended action.
- For Uran: you have scoped sudo to restart/inspect the Wayan services — use it
  only when needed, and say what you changed.

## Safety rules
- **Do not run destructive commands** (rm, mkfs, kill -9 on unrelated procs,
  package removal, config edits) unless the operator explicitly approves.
- Never touch `wayan-bot.service` or `/opt/wayan_pirat_bot`.
- Read-only playbook — do **not** edit this file.
- If you find an improvement, write a proposal in `skills/_proposals/`.
