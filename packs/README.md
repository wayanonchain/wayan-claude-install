# Profession Packs (v1)

A **pack** is a Markdown-only overlay that adapts the stock Wayan agents
(Jupiter + Uran) to a profession. Packs add **role emphasis, memory seeds,
routing rules, service mapping, and example commands** on top of the default
install. They add **no infrastructure**: no services, no env keys, no
permissions, no new skills — and they never disable the default skills.

Install with one:

```bash
WAYAN_PACK=onchain sudo -E ./install.sh
WAYAN_PACK=creator sudo -E ./install.sh
WAYAN_PACK=devops  sudo -E ./install.sh
WAYAN_PACK=student sudo -E ./install.sh
WAYAN_PACK=founder sudo -E ./install.sh
```

No `WAYAN_PACK` = the default install, byte-for-byte identical to before packs
existed. Full guide: [`docs/PACKS.md`](../docs/PACKS.md). Pack design notes per
profession: [`docs/PROFESSION_PACKS.md`](../docs/PROFESSION_PACKS.md).

## Layout of a pack

```
packs/<name>/
├── pack.md                      # what the pack is + what gets copied where
├── jupiter/PACK.md              # → <jupiter ws>/PACK.md   (role overlay)
├── uran/PACK.md                 # → <uran ws>/PACK.md      (role overlay)
├── memory/cold.md               # → <ws>/orchestration/memory/cold.md (seed)
├── rules/<name>-routing.md      # → <ws>/orchestration/rules/        (additive)
└── mapping/<name>-services.md   # → <ws>/orchestration/mapping/      (additive)
```

## Rules for all packs

- **No-clobber.** The installer never overwrites an existing file. A pack only
  fills gaps; user edits always win.
- **Deployed before defaults.** The pack's `memory/cold.md` is copied before the
  generic one, so the pack seed wins on a fresh install — and an already-filled
  `cold.md` is never touched on re-install.
- **Markdown only.** No YAML/JSON manifests in v1. If a file can't be expressed
  as Markdown read by the agent, it doesn't belong in a pack.
- **No secrets.** Packs are public templates — tokens, keys, chat IDs, and
  account handles belong in env files or the git-ignored `mapping/accounts.md`.
- **Default skills stay.** Packs may emphasize and re-route the six stock
  skills; they must not remove or contradict them.
