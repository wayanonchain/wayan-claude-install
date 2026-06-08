# Wayan Claude Agents — Installer (Day 1)

A clean, self-contained installer that provisions **two Claude Code agents** on
an Ubuntu VPS, following the EdgeLab "Day 1" methodology.

> This is an independent installer. It is **not** tied to any previous
> `wayan_pirat_bot` setup.

---

## 1. What we install

- **Jupiter** — the main daily agent (code, Telegram, projects).
- **Uran** — the backup / root-fix agent (repairs Jupiter, reads logs,
  restarts services, second independent channel).
- Node.js 22, Python 3, Claude Code, and supporting packages.
- Two `systemd` services, env files, a workspace, and a scoped `sudoers` rule.

---

## 2. Architecture

```
Ubuntu VPS (22.04 / 24.04)
└── user: wayan
    ├── /home/wayan/.claude-lab/
    │   ├── jupiter/   (CLAUDE.md, USER.md)   ← main agent workspace
    │   └── uran/      (CLAUDE.md, USER.md)   ← backup agent workspace
    ├── /opt/wayan-jupiter   ← Jupiter code/tools
    ├── /opt/wayan-uran      ← Uran code/tools
    ├── /etc/wayan-jupiter.env   (TELEGRAM_BOT_TOKEN=…)
    ├── /etc/wayan-uran.env      (TELEGRAM_BOT_TOKEN=…)
    ├── /etc/sudoers.d/wayan-agents
    └── systemd:
        ├── wayan-jupiter.service
        └── wayan-uran.service
```

---

## 3. Why two agents

A single agent is a single point of failure. If it crashes, hangs, or its
service dies, nobody can recover it remotely.

- **Jupiter** does the daily work.
- **Uran** is an independent watchdog with its own Telegram bot, its own
  service, and just enough `sudo` to inspect logs and restart Jupiter.

If Jupiter goes down, you message Uran and it brings Jupiter back.

---

## 4. Prerequisites

- A fresh Ubuntu **22.04** or **24.04** VPS.
- `root` (or `sudo`) access.
- Two Telegram bot tokens (one per agent — see sections 8–9).
- An Anthropic account to log in to Claude Code.

---

## 5. Local preparation (GitHub)

```bash
git clone https://github.com/wayanonchain/wayan-claude-install.git
cd wayan-claude-install
# inspect install.sh and scripts/ before running anything on a VPS
```

Repository layout:

```
wayan-claude-install/
├── README.md
├── install.sh
├── scripts/
│   ├── cleanup.sh
│   ├── update.sh
│   ├── uninstall.sh
│   └── healthcheck.sh
├── templates/
│   ├── jupiter/{CLAUDE.md,USER.md}
│   └── uran/{CLAUDE.md,USER.md}
├── systemd/
│   ├── wayan-jupiter.service
│   └── wayan-uran.service
└── tests/
    └── verify.sh
```

---

## 6. Install on the VPS

One-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/wayanonchain/wayan-claude-install/main/install.sh | sudo bash
```

Or from a clone:

```bash
sudo ./install.sh
```

The installer is **idempotent** — re-running it will not break an existing
install (env files and edited templates are preserved).

If you are reinstalling, clean up first:

```bash
sudo bash scripts/cleanup.sh
```

---

## 7. Authorize Claude Code

Claude Code is installed per-user for `wayan`. Log in once:

```bash
sudo -u wayan -i
claude        # follow the login flow, then exit
```

---

## 8. Telegram bot token — Jupiter

1. In Telegram, open **@BotFather** → `/newbot` → create the **Jupiter** bot.
2. Copy the token.
3. Put it in the env file:

```bash
sudoedit /etc/wayan-jupiter.env
# TELEGRAM_BOT_TOKEN=123456:ABC...
sudo systemctl restart wayan-jupiter.service
```

---

## 9. Telegram bot token — Uran

Use a **separate** bot so Uran stays an independent channel.

1. **@BotFather** → `/newbot` → create the **Uran** bot.
2. Copy the token.
3. Put it in the env file:

```bash
sudoedit /etc/wayan-uran.env
# TELEGRAM_BOT_TOKEN=987654:XYZ...
sudo systemctl restart wayan-uran.service
```

---

## 10. Verify

```bash
sudo bash scripts/healthcheck.sh
sudo bash tests/verify.sh

# live logs
journalctl -u wayan-jupiter.service -f
journalctl -u wayan-uran.service -f
```

---

## 11. Update

```bash
cd wayan-claude-install
sudo bash scripts/update.sh
```

Pulls the latest repo, re-runs the installer, restarts services, prints status.

---

## 12. Uninstall

Soft (keep user + home), so you can reinstall fresh:

```bash
sudo bash scripts/cleanup.sh
```

Full (removes workspaces, and the `wayan` user **only if** this installer
created it):

```bash
sudo bash scripts/uninstall.sh   # type DELETE to confirm
```

---

## 13. Troubleshooting

| Symptom | Check |
| --- | --- |
| `must run as root` | use `sudo` |
| `Unsupported Ubuntu` | only 22.04 / 24.04 are supported |
| Service won't start | `journalctl -u wayan-jupiter.service -e` |
| `claude: command not found` | log in once as `wayan` (section 7) |
| Telegram silent | token set in the right `.env`? service restarted? |
| sudoers error | `sudo visudo -cf /etc/sudoers.d/wayan-agents` |
| Need a clean slate | `sudo bash scripts/cleanup.sh` then reinstall |

> **Note:** The `ExecStart` lines in the `systemd/*.service` files are
> placeholders (they load the env and idle). Replace them with the real
> Jupiter/Uran entrypoints once the agent code is in place.
