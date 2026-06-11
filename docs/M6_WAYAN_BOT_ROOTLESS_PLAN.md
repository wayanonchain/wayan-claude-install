# M6 Phase 2 — Rootless hardening plan for `wayan-bot` (legacy bot)

**Status: AUDIT / DESIGN ONLY — nothing on the server has been changed.**
Audited 2026-06-11 on the production host, read-only. Applies to the legacy
`wayan_pirat_bot` service, which is *outside* this repo (it has its own git
repo at `/opt/wayan_pirat_bot/.git`). Jupiter/Uran/OpenViking are not touched
by this plan.

---

## 1. Current `wayan-bot.service` (as deployed)

| Directive | Value | Assessment |
| --- | --- | --- |
| `User=` / `Group=` | **absent → runs as root** | the problem |
| `ExecStart` | `/opt/wayan_pirat_bot/venv/bin/python main.py` | unprivileged-safe |
| `WorkingDirectory` | `/opt/wayan_pirat_bot` | fine |
| `EnvironmentFile` | **absent** — app loads `.env` itself via `python-dotenv` (`config/settings.py:8-11`) | bot user must be able to read `.env` |
| `Restart` / `RestartSec` | `always` / `5` | fine; note: a perms mistake ⇒ fast crash-loop |
| `TimeoutStopSec` / `KillMode` | `30` / `mixed` | fine |
| Hardening | **none** (no `NoNewPrivileges`, `ProtectSystem`, `PrivateTmp`, …) | to add |

Companion units: `wayan-healthcheck.timer` (every 3 min) → `healthcheck.sh`,
which curls `127.0.0.1:8080/health`, keeps state in
`/var/lib/wayan-bot/health_failures`, captures `py-spy` dumps to
`/var/log/wayan-bot`, and `systemctl restart`s the bot after 2 consecutive
failures. **It must stay root** (systemctl + ptrace + /var paths) — no change.

## 2. Ownership & permissions today

Everything under `/opt/wayan_pirat_bot` is `root:root`:

| Path | Mode | Notes |
| --- | --- | --- |
| code (`*.py`, `api/ bot/ core/ config/ db/ webhook/ scripts/ tests/`) | 755/644 | world-readable — fine to keep root-owned (bot can't self-modify = a feature) |
| `venv/` | 755 root | read+exec is enough for the bot user |
| `data/` → `bot.db`, `bot.db-wal`, `bot.db-shm` (live WAL) | 755/644 root | **must become writable by the bot user** |
| `.env` (+3 old backups) | ~~644 root — world-readable~~ → **600 root:root, fixed 2026-06-11** (standalone quick win applied; ownership stays root until the de-root cutover) | done |
| `backups/` | 755 root | manual snapshots; keep root |
| `.git/` | 755 root | keep root |
| `/opt/bot_log.txt` (+ rotations `.1..3`) | 644 root | see blocker below |
| `/var/lib/wayan-bot`, `/var/log/wayan-bot` | root | healthcheck-only; keep root |

## 3. What the bot actually writes (from code + live `lsof`)

1. `data/` — SQLite WAL trio (`bot.db`, `-wal`, `-shm`) + `DATA_DIR.mkdir(exist_ok=True)` at import (`config/settings.py:27`).
2. `/opt/bot_log.txt` — `RotatingFileHandler`, 5 MB × 3 (`main.py:22-26`).
3. `/tmp` — aiohttp internals only (`PrivateTmp` is safe).
4. Nothing else: no subprocess/sudo/systemctl calls anywhere in the bot code;
   Nansen reports and Telegram polling are **outbound HTTPS + DB writes only**;
   `/webhook/health` endpoints write nothing; `publish_free_course.py` is not
   wired to any unit/cron.

## 4. Root-only dependencies

| Candidate | Verdict |
| --- | --- |
| Port `127.0.0.1:8080` | unprivileged — no root needed |
| systemctl / restarts | only `healthcheck.sh` does this — stays root, separate unit |
| `py-spy` ptrace of the bot | healthcheck runs as root; root may ptrace a non-root process — still works |
| cron/sockets | none found |
| **Conclusion** | **the bot itself needs root for nothing** |

### ⚠️ Blocker found: log location

`LOG_DIR = Path(__file__).parent.parent` resolves to **`/opt`** — the bot
writes `bot_log.txt` into `/opt` itself, and log *rotation* needs write
permission **on the `/opt` directory** (rename/create). Options:

- **(chosen)** one-line change in the bot's `main.py`:
  `LOG_DIR = Path(__file__).parent / "logs"` — committed to the bot's own git
  repo, with `logs/` owned by the bot user. Clean, reviewable, reversible.
- (rejected) ACL granting the bot user write on `/opt`: directory-write means
  it could unlink/rename `/opt/wayan-jupiter` etc. Unacceptable.
- (rejected) pre-create files and accept broken rotation: log grows unbounded.

## 5. Target user model

- New system user **`wayan-bot`** (`useradd --system`, no shell
  `/usr/sbin/nologin`, no home dir needed; group `wayan-bot`).
  *Not* reusing the `wayan` user — Jupiter/Uran must not be able to read the
  legacy bot's keys, and vice versa.
- `chown wayan-bot:wayan-bot` — **only**:
  - `/opt/wayan_pirat_bot/data` (recursive — db + wal + shm live here)
  - `/opt/wayan_pirat_bot/.env` → then `chmod 600` (also `chmod 600` the three
    old `.env.bak*` files, owner root — they hold previous keys)
  - `/opt/wayan_pirat_bot/logs/` (new dir, after the LOG_DIR fix)
- **Stays root-owned** (read-only to the bot): all code, `venv/`, `backups/`,
  `.git/`, `scripts/`, `/var/lib/wayan-bot`, `/var/log/wayan-bot`,
  the systemd units. Python won't be able to refresh `__pycache__` — harmless
  (caches exist; on code changes root regenerates them or they're skipped).

## 6. Target unit (mirrors the proven wayan-jupiter hardening set)

```ini
[Service]
User=wayan-bot
Group=wayan-bot
WorkingDirectory=/opt/wayan_pirat_bot
ExecStart=/opt/wayan_pirat_bot/venv/bin/python main.py
Restart=always
RestartSec=5
TimeoutStopSec=30
KillMode=mixed
Environment=PYTHONUNBUFFERED=1
LimitNOFILE=65536
# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/wayan_pirat_bot/data /opt/wayan_pirat_bot/logs
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
LockPersonality=true
SystemCallArchitectures=native
```

Deliberately **not** included: `MemoryDenyWriteExecute` (CPython/uvloop JIT-ish
allocations can trip it), `IPAddressDeny` (bot needs broad outbound HTTPS).
`EnvironmentFile=` stays absent — dotenv keeps working unchanged.

## 7. Risk analysis

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Missed write path ⇒ crash-loop every 5 s | medium | Stage A dry-run as the new user *before* touching the unit; watch journal 10 min after cutover |
| `.env` unreadable ⇒ instant startup fail | low | explicit `runuser … cat .env` check in Stage A |
| SQLite WAL files recreated with wrong owner | low | chown `data/` *recursively* while service is **stopped** (WAL checkpointed on clean stop) |
| Log rotation breaks (`/opt` not writable) | certain without fix | LOG_DIR one-liner is part of the plan (Stage C) |
| `ProtectSystem=strict` blocks an unknown path | medium | first cutover may use `ProtectSystem=full` + tighten to `strict` after 24 h clean journal |
| healthcheck py-spy stops working | very low | root ptracing non-root child is allowed; verify dump in Stage E |
| Telegram polling / Nansen reports | none — outbound only | post-cutover live check anyway |

**Estimated downtime:** 30–60 s (one stop/start). Crash-loop worst case:
rollback in < 2 min from backups.

## 8. Staged migration plan (for the future "apply" session)

**Stage A — create user + dry-run (no service impact)**
```bash
useradd --system --shell /usr/sbin/nologin --no-create-home wayan-bot
runuser -u wayan-bot -- test -r /opt/wayan_pirat_bot/main.py && echo code-readable
runuser -u wayan-bot -- /opt/wayan_pirat_bot/venv/bin/python -c "import aiogram, uvicorn; print('venv ok')"
# .env/data are still root-owned here — A only proves read/exec of code+venv
```

**Stage B — stop + backup (downtime starts)**
```bash
systemctl stop wayan-bot.service && systemctl is-active wayan-bot || true
cp -a /opt/wayan_pirat_bot/data /opt/wayan_pirat_bot/data.bak.$(date +%Y%m%d-%H%M%S)
cp -a /opt/wayan_pirat_bot/.env /opt/wayan_pirat_bot/.env.bak.$(date +%Y%m%d-%H%M%S)
cp -a /etc/systemd/system/wayan-bot.service /etc/systemd/system/wayan-bot.service.bak.$(date +%Y%m%d-%H%M%S)
# ownership manifest for exact rollback:
find /opt/wayan_pirat_bot -printf '%u:%g %m %p\n' > /root/wayan_bot_ownership.before.txt
```

**Stage C — minimal chown + log fix**
```bash
cd /opt/wayan_pirat_bot
# LOG_DIR one-liner in main.py (commit to the bot's own git first):
#   LOG_DIR = Path(__file__).parent / "logs"
mkdir -p logs && chown wayan-bot:wayan-bot logs
chown -R wayan-bot:wayan-bot data
chown wayan-bot:wayan-bot .env && chmod 600 .env
chmod 600 .env.bak* .env.backup-*          # stay root-owned, stop world-read
```

**Stage D — unit update**
```bash
# install the [Service] block from §6 into /etc/systemd/system/wayan-bot.service
systemd-analyze verify /etc/systemd/system/wayan-bot.service
systemctl daemon-reload
```

**Stage E — start + verify (downtime ends)**
```bash
systemctl start wayan-bot.service && sleep 5 && systemctl is-active wayan-bot
ps -o user= -p "$(systemctl show wayan-bot -p MainPID --value)"   # expect: wayan-bot
ss -tlnp | grep 8080                                              # expect: 127.0.0.1
curl -fsS -m 5 http://127.0.0.1:8080/health                       # expect: {"status":"ok",...}
bash /opt/wayan_pirat_bot/scripts/healthcheck.sh; echo rc=$?      # expect: rc=0
journalctl -u wayan-bot -f   # watch ≥10 min: polling, scheduler, no PermissionError
# live test: send the bot a command in Telegram; confirm next Nansen scheduled post
```

**Stage F — rollback (if anything is wrong)**
```bash
systemctl stop wayan-bot
cp -a /etc/systemd/system/wayan-bot.service.bak.<TS> /etc/systemd/system/wayan-bot.service
systemctl daemon-reload
chown -R root:root /opt/wayan_pirat_bot/data /opt/wayan_pirat_bot/logs /opt/wayan_pirat_bot/.env
git -C /opt/wayan_pirat_bot checkout -- main.py    # undo LOG_DIR change
systemctl start wayan-bot && systemctl is-active wayan-bot
# exact ownership restore if ever needed: /root/wayan_bot_ownership.before.txt
```

## 9. Recommendation

**Apply later, in a quiet window — worth doing, not urgent.** The high-severity
exposure (world-reachable unauthenticated port) was already closed in Phase 1;
the bot now listens on localhost only. Remaining benefit of Phase 2 is
defense-in-depth (a bot compromise no longer equals root) plus fixing the
world-readable `.env`. Two notes:

- The **`chmod 600 .env*`** part — **applied 2026-06-11** (all four files:
  `.env` + 3 historical backups, 644 → 600, ownership left `root:root` since
  the service still runs as root; no content change, no restart needed;
  service `active` and healthcheck rc=0 verified after). Stage C of the
  migration shrinks accordingly: only the `chown wayan-bot` of `.env` remains.
- Tests required **before** applying: Stage A dry-runs green. **After**: full
  Stage E list (process user, port, /health, healthcheck rc=0, a real Telegram
  command answered, one scheduler cycle clean in journal, no `PermissionError`
  in 24 h) — then optionally tighten `ProtectSystem=full → strict`.

Out of scope here (unchanged): Helius stale webhook deletion (M6 phase 3),
Jupiter/Uran/OpenViking, RAM upgrade WARN.
