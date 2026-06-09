# Accounts (EXAMPLE — copy to accounts.md and fill in)

> This is a **template only**. Copy it to `accounts.md` (git-ignored) and put
> your real handles there. **Never put actual tokens/keys in any tracked file.**
> Tokens live in the env files and are referenced by name only.

## Telegram
- Jupiter bot: `@<jupiter_bot_username>` — token in `/etc/wayan-jupiter.env` as `TELEGRAM_BOT_TOKEN`
- Uran bot: `@<uran_bot_username>` — token in `/etc/wayan-uran.env` as `TELEGRAM_BOT_TOKEN`
- Operator chat id(s): `<chat_id>` (optionally set as `TELEGRAM_ALLOWED_CHAT_IDS`)

## GitHub
- Owner / repo: `<owner>/<repo>`
- Auth: `gh` CLI (token in the OS keyring, not here)

## Groq (voice)
- Key referenced as `GROQ_API_KEY` in `/etc/wayan-<agent>.env` (not stored here)

## Other external tools
- _(list any others by name; reference where the secret lives, never the secret)_

---
_Reminder: `accounts.md` must be in `.gitignore`. This example file is safe to
commit because it contains only placeholders._
