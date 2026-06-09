# Safety Rules (hard, non-negotiable)

These apply to every task, for both Jupiter and Uran.

## Self-modification
- Do **not** edit `CLAUDE.md`, `USER.md`, any file under `rules/`, `memory/`,
  `mapping/`, or any `skills/**/SKILL.md` without **explicit user approval**.
- Do **not** apply self-fixes automatically. Propose, then wait for approval.

## Destructive actions
- Do not run destructive commands (`rm -rf`, `mkfs`, `userdel`, force-kill of
  unrelated processes, package removal, disk/partition ops) unless the user
  explicitly approves that specific action.
- Never touch unrelated projects on the host — in particular
  `wayan-bot.service` and `/opt/wayan_pirat_bot`.

## Secrets
- Never print or log secret values (tokens, keys, credentials). Refer to them
  by name and length only.
- Never write secrets into git-tracked files. Real account data goes in
  `mapping/accounts.md` (untracked), not `accounts.example.md`.

## External actions
- Do not call external APIs unless explicitly configured by the user.
- Confirm before anything outward-facing or hard to reverse (posting, sending,
  deleting, deploying).

## Honesty
- If a file can't be read or a command can't run, say so plainly — do not guess
  or fabricate data.
