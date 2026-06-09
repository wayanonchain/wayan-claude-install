#!/usr/bin/env bash
#
# Wayan Claude Agents — export approved knowledge from the VPS into the repo.
#
# Pulls ONLY the approved knowledge directories from each agent's workspace and
# mirrors them into knowledge/<agent>/ in this repo. It then shows the git diff
# and STOPS. It never commits, never pushes, and never touches secrets.
#
# Whitelist (the ONLY things ever exported), per agent:
#   orchestration/memory             -> knowledge/<agent>/memory
#   orchestration/rules              -> knowledge/<agent>/rules
#   skills                           -> knowledge/<agent>/skills
#   orchestration/learnings/reviewed -> knowledge/<agent>/learnings-reviewed
#
# Never exported (by construction — they are simply not in the whitelist):
#   uploads/, outbox/, .claude/, /etc/*.env, mapping/accounts.md, learnings/inbox
#
# A secret scan runs on every pulled tree; if anything that looks like a token
# or key is found, the export ABORTS before writing into the repo.
#
# Usage:
#   bash scripts/export-knowledge.sh
#   WAYAN_VPS=root@1.2.3.4 bash scripts/export-knowledge.sh   # override host
#
set -euo pipefail

VPS="${WAYAN_VPS:-root@136.244.91.3}"
SSH_OPTS=(-o ConnectTimeout=20)
AGENTS=(jupiter uran)

# src-dir-in-workspace : dest-name-in-repo  (whitelist)
MAP=(
  "orchestration/memory:memory"
  "orchestration/rules:rules"
  "skills:skills"
  "orchestration/learnings/reviewed:learnings-reviewed"
)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_ROOT="${REPO_ROOT}/knowledge"

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# Patterns that should NEVER appear in exported knowledge.
SECRET_RE='TELEGRAM_BOT_TOKEN[[:space:]]*=[[:space:]]*[^[:space:]]|GROQ_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]]|gsk_[A-Za-z0-9]{20,}|[0-9]{6,}:[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY'

scan_secrets() {
  local dir="$1" label="$2"
  if grep -rIlEq "${SECRET_RE}" "${dir}" 2>/dev/null; then
    warn "Potential secret detected in ${label} — ABORTING (nothing written):"
    # Show WHERE, but redact the matched value.
    grep -rInE "${SECRET_RE}" "${dir}" 2>/dev/null \
      | sed -E 's/(:[0-9]+:).*/\1 <redacted match>/' \
      | sed "s|${dir}|${label}|" || true
    die "Export aborted to avoid leaking secrets. Clean the source on the VPS, then retry."
  fi
}

pull_one() {
  local agent="$1" src="$2" destname="$3"
  local base="/home/wayan/.claude-lab/${agent}"
  local dest="${DEST_ROOT}/${agent}/${destname}"

  if ! ssh "${SSH_OPTS[@]}" "${VPS}" "test -d '${base}/${src}'" 2>/dev/null; then
    warn "skip (absent on VPS): ${agent}/${src}"
    return
  fi

  local stage
  stage="$(mktemp -d "${TMPDIR:-/tmp}/wayan-knowledge.XXXXXX")"
  # Stream ONLY the contents of this one directory (no parents, no siblings).
  ssh "${SSH_OPTS[@]}" "${VPS}" "tar -C '${base}/${src}' -cf - ." | tar -C "${stage}" -xf -

  scan_secrets "${stage}" "${agent}/${destname}"

  # Replace the destination contents wholesale so removals on the VPS propagate.
  rm -rf "${dest}"
  mkdir -p "${dest}"
  cp -a "${stage}/." "${dest}/"
  rm -rf "${stage}"
  ok "exported ${agent}/${src} -> knowledge/${agent}/${destname}"
}

main() {
  command -v ssh >/dev/null || die "ssh not found."
  command -v tar >/dev/null || die "tar not found."
  log "Exporting approved knowledge from ${VPS} ..."
  log "Whitelist only; uploads/, .claude/, env files and secrets are never exported."

  for agent in "${AGENTS[@]}"; do
    log "Agent: ${agent}"
    for entry in "${MAP[@]}"; do
      pull_one "${agent}" "${entry%%:*}" "${entry##*:}"
    done
  done

  echo
  log "Changes staged in working tree (NOT committed):"
  git -C "${REPO_ROOT}" status --short -- knowledge/ || true
  echo
  log "Diff (knowledge/ only):"
  git -C "${REPO_ROOT}" --no-pager diff -- knowledge/ || true

  echo
  ok "Done. Nothing was committed or pushed."
  echo "Review the diff above. To publish AFTER review:"
  echo "    git add knowledge/ && git commit -m \"knowledge: export from VPS\" && git push"
}

main "$@"
