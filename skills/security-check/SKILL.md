---
name: security-check
description: Check tokens, links, contracts, env files, permissions and suspicious commands for risk.
read_only: true
---

# Security Check

## Purpose
Assess whether something is safe: a token/contract, a link, an env file, a set
of permissions, or a command someone is about to run.

## When to use
- Before acting on a link/contract/command of uncertain origin.
- The operator asks "is this safe?", "should I run this?", "is this a scam?".

## How to think
- Assume hostile intent until evidence says otherwise.
- For links/contracts: look for spoofed domains, lookalike tickers, drainer
  patterns, unverified contracts, dangerous approvals.
- For env/permissions: flag secrets in the wrong place, world-readable secrets,
  over-broad sudo, tokens that should be rotated.
- For commands: flag anything destructive, anything piping remote code to a
  shell, anything that exfiltrates data.
- **Never print secret values.** Refer to them by name and length only.

## Output format
For each finding:
- **Issue** — what it is
- **Severity** — `low` | `medium` | `high` | `critical`
- **Evidence** — what you observed (no secret values)
- **Recommendation** — what to do

## Rules
- Read-only playbook — do **not** edit this file.
- Do not call external APIs unless explicitly configured by the operator.
- If you find an improvement, write a proposal in `skills/_proposals/`.
