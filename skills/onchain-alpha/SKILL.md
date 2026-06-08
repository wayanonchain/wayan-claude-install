---
name: onchain-alpha
description: Analyze tokens — smart money, flows, holders, liquidity, scams, catalysts, market cap, risks and upside.
read_only: true
---

# Onchain Alpha

## Purpose
Evaluate a token end to end: what it is, who is buying, how money flows, how
risky it is, and whether there is real upside. Separate signal from noise.

## When to use
- The operator asks about a token, ticker, contract address, or chart.
- A task involves smart money, holders, liquidity, or "is this a scam?".

## How to think
- Start from the contract/chain and confirm you are looking at the right token.
- Weigh **onchain** evidence (flows, holders, liquidity, LP locks, mint/owner
  authorities) over hype.
- Call out scam patterns explicitly: honeypots, unlocked liquidity, mint
  authority, concentrated holders, fake volume, copycat tickers.
- Be honest about uncertainty. Do not invent numbers — if data isn't available,
  say so and state what you'd need.

## Output format
- **Token / chain / mcap** — name, ticker, chain, contract, market cap
- **What it does** — one or two lines
- **Why it matters** — the thesis (or lack of one)
- **Onchain signals** — smart money, flows, holders, liquidity, LP status
- **Risks** — scam vectors, concentration, liquidity, unlocks
- **Catalysts** — upcoming events, narratives, listings
- **Verdict** — `watch` | `avoid` | `deep dive` (one word + a sentence why)

## Rules
- Read-only playbook — do **not** edit this file.
- Do not call external APIs unless explicitly configured by the operator.
- If you find an improvement, write a proposal in `skills/_proposals/`.
