# Profession Packs — Installer Guide (v1)

## What a pack is

A **profession pack** is a Markdown-only overlay that adapts the stock Wayan
agents (Jupiter + Uran) to a profession at install time. A pack adds:

- **role emphasis** — a `PACK.md` in each workspace root that extends (never
  replaces) the agent's `CLAUDE.md`;
- **memory seeds** — a profession-shaped `orchestration/memory/cold.md`;
- **rules** — an additive routing/hard-rules file in `orchestration/rules/`;
- **mapping** — an additive services/tools map in `orchestration/mapping/`;
- **example commands** — so a new user knows what to ask on day one.

A pack adds **nothing else**. No services, no env keys, no permission changes,
no new skills, no manifests. The six stock skills stay installed and active
under every pack — packs only re-emphasize and re-route them.

v1 ships five packs: **onchain** (the current Wayan default, formalized),
**creator**, **devops**, **student**, **founder**.

## How to use a pack

```bash
git clone https://github.com/wayanonchain/wayan-claude-install.git
cd wayan-claude-install
WAYAN_PACK=onchain sudo -E ./install.sh
```

(`sudo -E` preserves `WAYAN_PACK` across sudo; `sudo WAYAN_PACK=onchain ./install.sh`
works too.)

No `WAYAN_PACK` (or empty) = the pack flow is skipped entirely and the install
behaves exactly as before packs existed.

Invalid or unknown pack names fail **before anything is installed**:

- the name must match `^[a-z][a-z0-9_-]{0,31}$`;
- `packs/<name>/pack.md` must exist — otherwise the installer aborts and
  prints the list of available packs.

## What gets copied where

The pack is deployed **before** the default templates/skills/orchestration, and
every copy is **no-clobber** (an existing file is never overwritten):

| Pack file | Destination |
| --- | --- |
| `packs/<p>/jupiter/PACK.md` | `/home/wayan/.claude-lab/jupiter/PACK.md` |
| `packs/<p>/uran/PACK.md` | `/home/wayan/.claude-lab/uran/PACK.md` |
| `packs/<p>/memory/cold.md` | `<ws>/orchestration/memory/cold.md` (both workspaces) |
| `packs/<p>/rules/*.md` | `<ws>/orchestration/rules/` (both workspaces) |
| `packs/<p>/mapping/*.md` | `<ws>/orchestration/mapping/` (both workspaces) |

Deploy order matters for one file: `memory/cold.md` exists both in the pack and
in the default orchestration tree. Because the pack is copied first and the
default copy is no-clobber, a fresh install gets the pack's seed — while a
re-install on a machine with an edited `cold.md` touches nothing.

Everything is `chown wayan:wayan`, mode 0640 (same as all other templates).

## How agents pick the pack up

Both `templates/*/CLAUDE.md` contain one generic hook line:

> If a `PACK.md` file exists in this workspace root, read it at session start —
> it extends this role with a profession pack.

No pack installed → no `PACK.md` → the line is a no-op. That is the entire
mechanism; there is no pack state anywhere else.

## How to create a new pack

1. Copy an existing pack: `cp -r packs/student packs/<name>`.
2. Rename the rules/mapping files to `<name>-routing.md` / `<name>-services.md`.
3. Rewrite the five content files for your profession:
   - `pack.md` — what it is + the copy table;
   - `jupiter/PACK.md`, `uran/PACK.md` — role emphasis, routing emphasis
     (stock skills only), example commands;
   - `memory/cold.md` — profession-shaped seed with `_(fill in)_` placeholders;
   - `rules/<name>-routing.md` — routing table + 3–5 hard rules;
   - `mapping/<name>-services.md` — tools map, **no secrets**.
4. Keep the v1 constraints: Markdown only, additive only, no infrastructure,
   no secrets, don't disable or contradict the stock skills.
5. `python3 -m unittest tests.test_packs` — the layout and no-secrets tests
   pick up new packs automatically.

Design guidance for which professions are worth a pack (and what each needs)
lives in [`PROFESSION_PACKS.md`](PROFESSION_PACKS.md).

## How to switch packs manually

Packs are just files, so switching on an installed system is file management
(do it as root, then fix ownership):

```bash
# 1. remove the old overlay (keep cold.md if you've filled it in!)
rm /home/wayan/.claude-lab/{jupiter,uran}/PACK.md
rm /home/wayan/.claude-lab/{jupiter,uran}/orchestration/rules/<old>-routing.md
rm /home/wayan/.claude-lab/{jupiter,uran}/orchestration/mapping/<old>-services.md

# 2. re-run the installer with the new pack (idempotent, no-clobber)
cd wayan-claude-install
WAYAN_PACK=<new> sudo -E ./install.sh
```

Note: your edited `orchestration/memory/cold.md` is never overwritten — merge
the new pack's seed (`packs/<new>/memory/cold.md`) into it by hand if you want
its structure. To go back to the default, just remove the overlay files
(step 1) and don't set `WAYAN_PACK`.

## Relation to PROFESSION_PACKS.md

[`PROFESSION_PACKS.md`](PROFESSION_PACKS.md) is the **design catalog**: eight
profession adaptations, what each would need, monetization and risk notes, and
the recipe for designing new ones. This document (`PACKS.md`) is the
**installer mechanism**: the five packs that actually ship in `packs/` and how
they are deployed. The catalog describes ideas (including future skills); the
shipped v1 packs implement the overlay parts only — stock skills, Markdown
overlays, nothing new to maintain.

## Why packs are Markdown-first

- **The agents are Markdown-driven.** `CLAUDE.md`, skills, rules, memory,
  mapping — everything an agent reads is Markdown. A pack in the same format
  needs no loader, no parser, no schema versioning.
- **No-clobber composes naturally.** Files either exist or don't; user edits
  always win; re-installs are safe. A manifest would need merge semantics.
- **Inspectable.** A user can read the entire effect of a pack with `cat`
  before installing it — important for a public template repo.
- **v2 can grow from it.** If packs ever need conditionals or versioning, a
  manifest can be added on top of these same files. Today it would be
  infrastructure without a user.
