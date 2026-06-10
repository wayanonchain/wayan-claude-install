# OpenViking — Long-Term Semantic Memory

OpenViking gives the Wayan agents (Jupiter and Uran) a **shared, long-term
semantic memory** — a vector index they can query by meaning, on top of the
plain-Markdown knowledge that remains the source of truth.

> **Secrets note:** the OpenAI key lives only in `~/.openviking/ov.conf` on the
> VPS (`chmod 600`, `wayan:wayan`). It is never committed, printed, or echoed.
> `.gitignore` blocks `.openviking/`, `ov.conf`, env files, and Claude
> credentials.

---

## Why OpenViking

Markdown files (`rules/`, `skills/`, `memory/`, `learnings/`, `transcripts/`)
are perfect as the **reviewable, versioned source of truth** — but they don't
scale to "find the thing I half-remember." OpenViking adds a **semantic recall
layer**: the agent embeds knowledge and later retrieves it by meaning, not exact
keywords. It solves "goldfish amnesia" without changing where the canonical
knowledge lives.

- **Source of truth:** Markdown in git (and the workspace).
- **Recall/index layer:** OpenViking (derived, rebuildable, not authoritative).

If OpenViking is wiped, nothing is lost — it can be re-indexed from the Markdown.

---

## Architecture

```
VPS (localhost only)
└── Docker Compose
    └── openviking  →  http://127.0.0.1:1933   (NOT exposed publicly)
        ├── config: /home/wayan/.openviking/ov.conf   (600, wayan:wayan)
        └── data:   /home/wayan/.openviking/data
   Provider: OpenAI
     - embeddings: text-embedding-3-small (dim 1536)
     - VLM:        gpt-4o-mini
```

- API listens on **localhost only** (`127.0.0.1:1933`). No firewall ports opened.
- Both agents talk to the **same** instance, so memory is shared between Jupiter
  and Uran.

---

## Where memory is stored

| Layer | Lives in | Role |
| --- | --- | --- |
| Canonical knowledge | git Markdown + workspace (`rules/`, `skills/`, `mapping/`, `learnings/reviewed/`, `transcripts/`) | Source of truth, reviewed |
| Tiered working context | `orchestration/memory/{hot,warm,cold}.md` | Short-term / durable context |
| Semantic recall | OpenViking (`~/.openviking/data`) | Index for meaning-based recall |

---

## What to store in OpenViking

**Do store** — short, structured, durable knowledge that benefits from recall:
- Stable facts (owner, timezone, project goals, conventions).
- Approved learnings and decisions (from `learnings/reviewed/`).
- Distilled summaries of transcripts/analyses (not the raw media).

**Keep only in git Markdown** (do not duplicate verbatim into OpenViking):
- Full rule text, full skill playbooks — these are versioned and reviewed.
- Anything that must be human-diffable and approved before it changes.

**Never store in OpenViking:**
- Secrets/tokens/keys, env values, credentials.
- Raw uploads (audio/video/images/documents).
- Full private logs/transcripts unless explicitly approved.

Prefer **short, structured entries** over dumping large blobs.

---

## How Jupiter and Uran share memory

Both agents are configured to use the same `http://127.0.0.1:1933` instance, so
a fact stored by Jupiter is recallable by Uran and vice-versa. There is one
shared semantic memory, not two.

---

## Auto-capture policy (default OFF)

```
AUTO_CAPTURE = false
```

By default, memory is written **only** via explicit `memory_store`. The agent may
*propose* "Store this in OpenViking?" after an important task, but it must not
auto-store sensitive/private data. Unrestricted auto-capture stays disabled until
explicitly enabled, to avoid filling memory with noise.

Enabled by default: manual `memory_store`, manual `memory_recall`, and
(optionally) auto-recall.

---

## Backup / restore

All state is under `~/.openviking`. To back up:

```bash
# stop, snapshot the data dir, restart
cd /home/wayan/.openviking
docker compose stop
sudo -u wayan tar -C /home/wayan/.openviking -czf \
  /home/wayan/.openviking/backups/ov-$(date +%Y%m%d-%H%M%S).tar.gz data
docker compose start
```

Restore = stop, replace `data/` from a backup tarball, start. Because OpenViking
is a derived index, you can alternatively rebuild it by re-storing from the
Markdown source of truth.

---

## How to disable

```bash
cd /home/wayan/.openviking
docker compose down        # stop containers (keeps data)
# or, to remove data too (irreversible):
# docker compose down && rm -rf /home/wayan/.openviking/data
```

Disabling OpenViking does not affect the agents' Markdown knowledge — they keep
working with the local source of truth; they simply lose semantic recall until
it's brought back up.

---

## Security recap

- Localhost-only (`127.0.0.1:1933`); never exposed to the internet; no firewall
  ports opened.
- Key only in `ov.conf` (`600`, `wayan:wayan`); never committed/printed.
- `.gitignore` blocks `.openviking/`, `ov.conf`, env files, and Claude creds.
- No secrets, raw uploads, or unapproved private logs go into the index.
