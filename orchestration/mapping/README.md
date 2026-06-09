# Mapping

A map of the world the agent operates in: infrastructure, services, and
accounts. **These are templates — fill them in for your own setup.**

| File | Holds | Secrets? |
| --- | --- | --- |
| `infrastructure.md` | Hosts, OS, where things live | no secrets — use placeholders |
| `services.md` | systemd services and how they're managed | no secrets |
| `accounts.example.md` | Shape of accounts/handles/tokens | **example only** |

## Important: secrets

- `accounts.example.md` is a **template**. Copy it to `accounts.md` and put real
  handles there. `accounts.md` is git-ignored and must **never** be committed.
- Never store actual tokens/keys here. Those live in the env files
  (`/etc/wayan-*.env`, mode 0640), referenced by name only.

## Customize first

New users should fill in `infrastructure.md`, `services.md`, and create
`accounts.md` from the example before relying on infrastructure tasks.
