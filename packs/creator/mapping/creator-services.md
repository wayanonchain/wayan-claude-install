# Creator Pack — External Services Map (customize this)

> Platforms and tools in the content pipeline. No secrets here — tokens/keys
> go in env files; handles go in the git-ignored `mapping/accounts.md`.

## Platforms (manual publish — agent drafts only)

| Platform | Content types | Analytics source |
| --- | --- | --- |
| TikTok | shorts | manual export / screenshot |
| Instagram Reels | shorts | manual export / screenshot |
| X | threads, posts | manual export / screenshot |
| YouTube | long + shorts | manual export / screenshot |
| _(prune to what you use)_ | | |

## Already-configured infrastructure (stock install)

| Service | Role |
| --- | --- |
| Telegram bots (Jupiter/Uran) | operator channel, voice/video intake |
| Groq Whisper | voice + video-audio transcription |
| ffmpeg + visual analysis (optional) | keyframes from uploaded videos |
| OpenViking (optional) | long-term memory, localhost-only |

## Rules

- The agent never logs into platforms and never posts. Drafts go back over
  Telegram (text or `outbox/` files).
- Analytics only from operator-provided exports, always dated.
