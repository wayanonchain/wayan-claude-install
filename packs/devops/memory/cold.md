# Cold Memory — devops pack seed (customize this)

> Long-standing facts that rarely change. First file to fill in after install.
> Updated only with operator approval. No secrets here.

## Operator
- Name / handle: _(fill in)_
- Role: _(e.g. solo dev / SRE / team lead)_
- Preferred language: _(fill in)_

## Stack
- Languages / frameworks: _(fill in)_
- Hosting: _(e.g. this VPS, plus …)_
- CI: _(e.g. GitHub Actions)_
- Repos that matter: _(names only, no tokens)_

## Services I run
> Keep in sync with `mapping/devops-services.md` (the authoritative allowlist).
- _(fill in: name — what it does — how critical)_

## Runbook pointers
- Where runbooks live: _(e.g. skills/, repo docs/)_
- Postmortems: `orchestration/learnings/` + `logs/failed/`

## Durable preferences
- Always do: diagnose before acting, write incident summaries, prefer
  reversible commands.
- Never do: restart non-allowlisted services, paste secrets/log dumps with
  tokens, apt/system upgrades without explicit approval.
