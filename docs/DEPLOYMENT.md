# Deployment — repo-first workflow

**GitHub is the single source of truth.** Production only ever runs code that
exists in `main`. This document is the contract that prevents repo/production
drift.

## Why this exists

During the visual-video-analysis milestone, gateway `1.1.0a11` was built and
deployed **directly on the VPS** while the repo still held `1.1.0a10`. The live
system worked, but the repo — the thing installs, audits, and rollbacks are
based on — was lying about what production ran. It was reconciled in commit
`6fcaadb`; this workflow makes sure it never happens again.

## Layout

| What | Where |
| --- | --- |
| Source of truth | `src/gateway/` in <https://github.com/wayanonchain/wayan-claude-install> (`main`) |
| Jupiter production | `/opt/wayan-jupiter/gateway/` (service `wayan-jupiter`) |
| Uran production | `/opt/wayan-uran/gateway/` (service `wayan-uran`) |
| Rollback points | `/opt/wayan-*/gateway.bak.YYYYMMDD-HHMMSS` (created by every deploy) |

Both `/opt` trees must always be byte-identical to the repo's `src/gateway/`
(`.py` files; `__pycache__` is ignored).

## Why direct VPS edits are dangerous

- The repo stops describing production: audits, `install.sh`, and fresh
  installs are silently wrong.
- The next `install.sh` / deploy **overwrites** your VPS-only edit — work lost.
- Jupiter and Uran can diverge from *each other* (edits applied to one tree).
- Untested code reaches production without the 98-test suite ever seeing it.
- There is no reviewable history of what changed, or why.

If you ever *must* hot-fix on the VPS (outage), copy the change back into the
repo and commit it **the same day**, then run a normal deploy so production is
once again repo-built.

## The correct workflow

```
edit repo → test → commit → push → deploy-gateway.sh → restart → verify
```

Concretely (on the VPS, in the repo checkout):

```bash
# 1. Get the latest main + run tests + see drift (read-only, safe anytime):
bash scripts/update.sh

# 2. Preview exactly what a deploy would do (changes nothing):
sudo bash scripts/deploy-gateway.sh --dry-run

# 3. Deploy with backup + restart + verification:
sudo bash scripts/deploy-gateway.sh --restart
```

`deploy-gateway.sh` refuses a dirty working tree (uncommitted changes are not
the source of truth) — `--allow-dirty` overrides for emergencies only. It
deploys to **both** agents, runs an import sanity check against each agent's
venv, and after `--restart` verifies both services are `active`.

## Checking drift

```bash
bash scripts/deploy-gateway.sh --check
```

Output (and exit code 0):

```
Repo gateway: src/gateway (version 1.1.0a11, branch main, commit abc1234)
Jupiter: /opt/wayan-jupiter/gateway
  identical (10 files)
Uran: /opt/wayan-uran/gateway
  identical (10 files)
Status: PASS, production matches repo
```

On drift it prints **file names only** (never contents, never secrets) as
`CHANGED` / `NEW` (in repo, not deployed) / `EXTRA` (deployed, not in repo) and
exits 1. Run it from your Mac any time:
`ssh wayan-vps 'cd /root/wayan-claude-install && bash scripts/deploy-gateway.sh --check'`.

## Rollback

Every deploy first copies the live tree aside:

```bash
ls -d /opt/wayan-jupiter/gateway.bak.*        # pick the timestamp you want
sudo rm -rf /opt/wayan-jupiter/gateway
sudo mv /opt/wayan-jupiter/gateway.bak.20260611-051234 /opt/wayan-jupiter/gateway
sudo systemctl restart wayan-jupiter.service
systemctl is-active wayan-jupiter.service     # must print: active
```

Repeat for Uran. Then fix the bad code **in the repo** and deploy normally.
Backups are kept indefinitely for now (pruning is a future, separate change).

## What the deploy scripts never touch

By construction, the only paths written are `/opt/wayan-*/gateway` (plus its
timestamped backups and a temporary staging dir). The scripts **never** read or
write:

- `/etc/wayan-*.env` — Telegram / Groq / OpenAI keys and feature flags
- any secret, key, or credential file; `ov.conf`; OpenViking data or config
  (OpenViking stays bound to `127.0.0.1:1933`)
- agent workspaces (`~wayan/.claude-lab/*`), venvs, or systemd units
- file permissions outside the deployed tree (deployed files are
  `chown wayan:wayan`, same as the installer)

As defense in depth, the deploy aborts if anything secret-shaped (`*.env`,
`ov.conf`, `*credential*`, `*.pem`, `id_*`) ever appears inside `src/gateway/`.

## Avoiding committed secrets

- Secrets live **only** in `/etc/wayan-*.env` on the VPS — never in the repo.
- `.gitignore` already excludes env files, uploads, and transcripts; don't
  fight it.
- Before any commit that touches scripts/code, scan the staged diff:
  `git diff --cached | grep -iE 'api[_-]?key|token|secret|password'`.
- If a secret does land in a commit: rotate the key first, then rewrite
  history — deleting the file in a follow-up commit is not enough.

## Known follow-up (separate security milestone — out of scope here)

A host service outside this repo (`/opt/wayan_pirat_bot`, root, Python) listens
on `0.0.0.0:8080`. It is deliberately **not** touched by this workflow; firewall
review / localhost binding is tracked as its own milestone in `ROADMAP.md`.
