# Storage Policy — Minimal Storage

The VPS does **not** permanently store heavy user uploads. Heavy files are
temporary; long-term knowledge is **Markdown**.

---

## Where uploaded files go

```
/home/wayan/.claude-lab/<agent>/
├── uploads/tmp/     # raw uploads land here — TEMPORARY
├── transcripts/     # Markdown transcripts/analyses — long-term knowledge
└── outbox/          # files the agent produces for you (delivered, then yours)
```

- **Voice/audio:** saved to `uploads/tmp/`, transcribed via Groq, written as a
  Markdown transcript in `transcripts/`, then the raw audio is deleted (unless
  `FILE_KEEP_ORIGINAL=true`).
- **Documents/images:** saved to `uploads/tmp/`, read by Claude, the analysis is
  written as a Markdown transcript in `transcripts/`, then the raw file is
  deleted (unless `FILE_KEEP_ORIGINAL=true`).

## When files are deleted

| File | Deleted when |
| --- | --- |
| Raw upload in `uploads/tmp/` | Immediately after a successful transcript, **if** `FILE_KEEP_ORIGINAL=false` (the default) |
| Raw upload (kept) | After `FILE_RETENTION_HOURS` (default 24h) by `cleanup-uploads.sh` |
| Markdown transcript | **Never** by the policy — it's the knowledge artifact |

Even with `FILE_KEEP_ORIGINAL=true`, raw files in `uploads/tmp/` are still
swept after the retention window — "keep" means "keep until cleanup," not
"forever."

## What gets preserved

`transcripts/`, `memory/`, `rules/`, `skills/`, `learnings/`, `mapping/`, env
files, and Claude credentials are **never** touched by cleanup. Only regular
files under `uploads/tmp/` are removed, and only by age.

## Settings (env, per agent)

| Key | Default | Meaning |
| --- | --- | --- |
| `FILE_KEEP_ORIGINAL` | `false` | Keep raw files after transcript? |
| `FILE_RETENTION_HOURS` | `24` | Age after which `uploads/tmp` files are swept |
| `TRANSCRIPTS_ENABLED` | `true` | Write Markdown transcripts |
| `TRANSCRIPTS_DIR` | `transcripts` | Workspace-relative transcript dir |
| `UPLOADS_TMP_DIR` | `uploads/tmp` | Workspace-relative temp upload dir |

## Cleanup

**Default: manual.** Run when you like:

```bash
bash scripts/cleanup-uploads.sh
# override retention:
FILE_RETENTION_HOURS=48 bash scripts/cleanup-uploads.sh
```

**Optional scheduled cleanup (disabled by default).** The installer does not
enable any timer. To schedule it:

```bash
sudo cp scripts/cleanup-uploads.sh /usr/local/bin/cleanup-uploads.sh
sudo chmod +x /usr/local/bin/cleanup-uploads.sh
sudo cp systemd/wayan-cleanup.service systemd/wayan-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wayan-cleanup.timer   # runs daily at 04:00
```

## Why Markdown is the long-term knowledge format

- **Reviewable & diffable** — plain text shows up cleanly in git diffs.
- **Portable & durable** — no binary lock-in; readable in any editor, forever.
- **Small** — a transcript is kilobytes; the source media is megabytes.
- **Safe to version** — text knowledge can be reviewed before it's committed.

## How to export approved Markdown knowledge to Git

Use the export tool (see [`KNOWLEDGE_EXPORT.md`](KNOWLEDGE_EXPORT.md)):

```bash
bash scripts/export-knowledge.sh   # pulls approved memory/rules/skills/reviewed
```

It shows a diff and stops; you review and commit deliberately. Transcripts reach
git only if you deliberately copy approved ones into `knowledge/`.

## Why raw uploads should not be committed

- They're **heavy** (audio/video/images) — they bloat the repo irreversibly.
- They may contain **private or sensitive** content the operator sent in chat.
- The **knowledge** is the transcript/analysis, not the raw bytes.

`.gitignore` enforces this: `uploads/` and root `transcripts/` are never
committed; only curated Markdown under `knowledge/` is.
