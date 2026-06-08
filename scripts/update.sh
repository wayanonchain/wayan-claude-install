#!/usr/bin/env bash
#
# Wayan Claude Agents — update
#
# Pulls the latest repo, re-runs the installer (idempotent), restarts services,
# and prints status. Env files and edited templates are preserved by install.sh.
#
set -euo pipefail

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

REPO_URL="https://github.com/wayanonchain/wayan-claude-install.git"

[[ "$(id -u)" -eq 0 ]] || die "update.sh must run as root (use sudo)."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -d "${SCRIPT_DIR}/.git" ]]; then
  log "Updating local checkout at ${SCRIPT_DIR} ..."
  git -C "${SCRIPT_DIR}" pull --ff-only || die "git pull failed."
  REPO_DIR="${SCRIPT_DIR}"
else
  log "No local git checkout; cloning fresh copy ..."
  REPO_DIR="$(mktemp -d /tmp/wayan-update.XXXXXX)"
  git clone --depth 1 "${REPO_URL}" "${REPO_DIR}" || die "git clone failed."
fi

log "Re-running installer (idempotent) ..."
bash "${REPO_DIR}/install.sh"

log "Restarting services ..."
systemctl restart wayan-jupiter.service 2>/dev/null || true
systemctl restart wayan-uran.service    2>/dev/null || true

log "Service status:"
systemctl --no-pager --full status wayan-jupiter.service || true
systemctl --no-pager --full status wayan-uran.service    || true

ok "Update complete."
