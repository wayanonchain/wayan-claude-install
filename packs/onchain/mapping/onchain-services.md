# Onchain Pack — External Services Map (customize this)

> Data sources the agents may cite for onchain research. **Read-only, public
> web data only** — no keys here. API keys (if any) go in env files; account
> handles go in the git-ignored `mapping/accounts.md`.

## Explorers / data (allowed to cite)

| Service | Use for | Notes |
| --- | --- | --- |
| Dexscreener | DEX pairs, price, liquidity | public web |
| Solscan | Solana txs, holders, tokens | public web |
| Etherscan | EVM txs, contracts, holders | public web |
| _(add yours)_ | | |

## Already-configured infrastructure (stock install)

| Service | Role |
| --- | --- |
| Telegram bots (Jupiter/Uran) | operator channel |
| Groq Whisper | voice/video transcription |
| OpenViking (optional) | long-term memory, localhost-only |

## Rules

- Cite the source next to every number ("per Solscan, as of YYYY-MM-DD").
- If a needed source is not in this table, ask the operator before using it.
- Never use sources that require connecting a wallet.
