# Costs & Services

What you need to run this, and roughly what it costs. **Prices change** — always
check the official pages (linked) for current numbers. Figures below are rough
"order of magnitude," not quotes.

---

## Required

| Service | What it's for | Typical cost | Official pricing |
| --- | --- | --- | --- |
| **VPS** (Ubuntu 22/24) | Where the agents actually run, 24/7 | ~$5–12 / month for 1–2 GB RAM* | e.g. [Vultr](https://www.vultr.com/pricing/), [Hetzner](https://www.hetzner.com/cloud), [DigitalOcean](https://www.digitalocean.com/pricing/droplets) |
| **GitHub** | Hosts your repo / versioned knowledge | Free for public & private repos | [github.com/pricing](https://github.com/pricing) |
| **Telegram + BotFather** | The chat interface to Jupiter & Uran | Free | [core.telegram.org/bots](https://core.telegram.org/bots) |
| **Claude Code** | The agent brain (`claude -p`) | Paid plan or API usage | [claude.com/pricing](https://claude.com/pricing), [anthropic.com/pricing](https://www.anthropic.com/pricing) |
| **Groq** | Voice → text transcription (Whisper) | Pay-as-you-go; small per-minute audio cost | [groq.com/pricing](https://groq.com/pricing) |
| **OpenAI** | Embeddings + extraction for OpenViking memory | Pay-as-you-go; **fund ≥ $5** to start | [openai.com/api/pricing](https://openai.com/api/pricing) |

\* **RAM matters:** OpenViking + the agents are happier with **2 GB**. A 1 GB box
works but may swap (see the storage/RAM notes in the main README).

---

## Optional

| Service | What it's for | Cost | Link |
| --- | --- | --- | --- |
| **Obsidian** | A nice local editor for your Markdown knowledge | Free for personal use | [obsidian.md](https://obsidian.md) |

---

## Rough monthly picture (light personal use)

- **Fixed:** VPS (~$5–12).
- **Usage-based:** Claude (depends on plan/usage), Groq (cents per voice minute),
  OpenAI embeddings (`text-embedding-3-small` is very cheap) + the `gpt-4o-mini`
  memory extractor (a few cents per stored memory).
- **Free:** GitHub, Telegram, Obsidian.

A hobby setup is typically dominated by the **VPS** plus your **Claude** usage;
Groq and OpenAI are usually small.

---

## Notes on keys & billing

- Each paid service needs an **API key** (Groq, OpenAI) or a **token** (Telegram).
  These live in `600`-permission files on the server and are **never committed**
  (see [`PUBLIC_TEMPLATE_GUIDE.md`](PUBLIC_TEMPLATE_GUIDE.md)).
- OpenAI requires a **funded balance** (≥ $5) before embeddings/extraction work —
  otherwise OpenViking memory will fail to store.
- Set spend limits in each provider's dashboard if you're cost-conscious.

> ⚠️ All prices are indicative and **subject to change** by the providers. Check
> the official links above before committing to a plan.
