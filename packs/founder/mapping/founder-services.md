# Founder Pack — Tools Map (customize this)

> Tools in the founder's pipeline. No secrets here — keys go in env files;
> account handles go in the git-ignored `mapping/accounts.md`.

## Document & research tools

| Tool | Use | Notes |
| --- | --- | --- |
| GitHub | docs versioning (memos, notes) | repo names only |
| _(CRM / notes tool)_ | _(fill in)_ | |
| _(cap table / data room)_ | _(fill in)_ | agent never gets access — names only |

## Already-configured infrastructure (stock install)

| Service | Role |
| --- | --- |
| Telegram bots (Jupiter/Uran) | operator channel, file/voice intake |
| Groq Whisper | call/voice transcription |
| OpenViking (optional) | long-term memory, localhost-only |
| `outbox/` in workspace | documents delivered back over Telegram |

## Rules

- The agent drafts; the operator sends. No email/investor-portal access, ever.
- Data rooms and anything under NDA are referenced by name only — contents
  arrive only as operator-provided uploads, handled under minimal storage.
