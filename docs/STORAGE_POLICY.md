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

## Upload-size protection (two-step safety)

Large files are not blindly rejected by one static number — they pass a two-step
check before anything is downloaded.

### 1. Static type limit
The file's type and size are read from Telegram metadata **before download** and
compared to a per-type limit:

| Type | Env | Default |
| --- | --- | --- |
| Video | `VIDEO_MAX_MB` | 250 |
| Audio | `AUDIO_MAX_MB` | 100 |
| Document | `DOCUMENT_MAX_MB` | 50 |
| Image | `IMAGE_MAX_MB` | 25 |
| (fallback) | `FILE_MAX_MB` | 100 |

Over the limit → **rejected, not downloaded**:

```
❌ File too large

Type: video
Size: 684 MB
Limit: 250 MB

Please upload a smaller file or provide a link.
```

### 2. Disk availability
Before downloading any file at/above `LARGE_FILE_CONFIRM_MB` (25), the gateway
checks free space on the workspace filesystem and requires:

```
required = size_mb * DISK_REQUIRED_MULTIPLIER + DISK_MIN_FREE_MB
         = size_mb * 2 + 2048
```

Not enough → **rejected, not downloaded**:

```
❌ Not enough disk space

File size: 180 MB
Required free space: 2408 MB
Available free space: 900 MB

Please free disk space or send a smaller file.
```

### 3. PROCESS FILE confirmation
If a file is large but within its limit and disk is sufficient, the gateway
**warns and waits** — nothing is downloaded until you confirm:

```
⚠️ Large file detected

Type: video
Size: 180 MB
Limit: 250 MB
Available disk: 17 GB
Estimated temporary usage: up to 360 MB

Reply with:
PROCESS FILE

to continue.
```

Reply **`PROCESS FILE`** to proceed. The pending confirmation expires after
`UPLOAD_CONFIRMATION_TIMEOUT_MIN` (15 min), and disk space is **re-checked**
right before the download (it may have filled up while you decided).

Small files (under `LARGE_FILE_CONFIRM_MB`) skip all of this and process
immediately.

### Large-video workflow & a hard Telegram limit

> **Important:** the Telegram **Bot API caps file downloads at 20 MB.** Even
> though `VIDEO_MAX_MB` allows 250 MB by policy, a bot generally *cannot*
> download a file larger than 20 MB via `getFile` — the download will fail.
> For anything bigger, **send a link** (e.g. a cloud/storage URL) instead of the
> raw file, and ask the agent to work from the link. Raising the real ceiling
> requires a self-hosted Telegram Bot API server, which is out of scope here.

### Settings

| Key | Default | Meaning |
| --- | --- | --- |
| `LARGE_FILE_CONFIRM_MB` | `25` | At/above this size, confirm + disk-check |
| `DISK_MIN_FREE_MB` | `2048` | Safety buffer that must remain free |
| `DISK_REQUIRED_MULTIPLIER` | `2` | Multiple of file size required free |
| `UPLOAD_CONFIRMATION_TIMEOUT_MIN` | `15` | Pending-confirmation lifetime |

### Logged events
`large_upload_pending`, `large_upload_confirmed`, `large_upload_expired`,
`upload_rejected_size`, `upload_rejected_disk`, `upload_processed`.

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
