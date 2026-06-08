#!/usr/bin/env bash
#
# Wayan Claude Agents — apply CLAUDE.md template updates to existing workspaces.
#
# The installer is intentionally no-clobber and never overwrites a workspace
# CLAUDE.md. This script is the *explicit* path to push updated CLAUDE.md from
# the repo templates into the live workspaces, with a timestamped backup.
#
# - Backs up each existing CLAUDE.md -> CLAUDE.md.bak.<timestamp>
# - Overwrites CLAUDE.md from templates/<agent>/CLAUDE.md
# - Does NOT touch USER.md, env files, skills, or Claude credentials.
#
# Usage:
#   sudo bash scripts/apply-templates.sh
# or (no local clone):
#   curl -fsSL https://raw.githubusercontent.com/wayanonchain/wayan-claude-install/main/scripts/apply-templates.sh | sudo bash
#
set -euo pipefail

REPO_URL="https://github.com/wayanonchain/wayan-claude-install.git"
WAYAN_USER="wayan"
LAB_DIR="/home/${WAYAN_USER}/.claude-lab"

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "must run as root (use sudo)."

# Resolve templates source: local repo if present, else clone.
SRC_DIR=""
CLONED_TMP=""
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
if [[ -n "${script_dir}" && -d "${script_dir}/templates" ]]; then
  SRC_DIR="${script_dir}"
  ok "Using local templates at ${SRC_DIR}/templates."
else
  log "No local templates; cloning ${REPO_URL} ..."
  CLONED_TMP="$(mktemp -d /tmp/wayan-templates.XXXXXX)"
  git clone --depth 1 "${REPO_URL}" "${CLONED_TMP}" >/dev/null 2>&1 \
    || die "clone failed."
  SRC_DIR="${CLONED_TMP}"
fi
cleanup() { [[ -n "${CLONED_TMP}" && -d "${CLONED_TMP}" ]] && rm -rf "${CLONED_TMP}"; }
trap cleanup EXIT

apply_one() {
  local agent="$1"
  local src="${SRC_DIR}/templates/${agent}/CLAUDE.md"
  local ws="${LAB_DIR}/${agent}"
  local dst="${ws}/CLAUDE.md"

  [[ -f "${src}" ]] || die "template not found: ${src}"
  [[ -d "${ws}" ]]  || { warn "workspace missing, skipping: ${ws}"; return; }

  if [[ -f "${dst}" ]]; then
    local backup="${dst}.bak.$(date +%Y%m%d-%H%M%S)"
    cp -p "${dst}" "${backup}"
    chown "${WAYAN_USER}:${WAYAN_USER}" "${backup}"
    ok "backed up ${dst} -> ${backup}"
  else
    warn "no existing ${dst} (creating fresh)."
  fi

  install -m 0640 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${src}" "${dst}"
  ok "applied template -> ${dst}"
  # USER.md is intentionally left untouched.
}

log "Applying CLAUDE.md template updates (USER.md untouched) ..."
apply_one jupiter
apply_one uran

log "Verifying ..."
for agent in jupiter uran; do
  dst="${LAB_DIR}/${agent}/CLAUDE.md"
  if grep -q "## Skills Usage" "${dst}" 2>/dev/null; then
    ok "${dst} contains '## Skills Usage'"
  else
    warn "${dst} missing '## Skills Usage'"
  fi
done

ok "Done. Backups: ${LAB_DIR}/<agent>/CLAUDE.md.bak.<timestamp>"
ok "Restart not required — Claude reads CLAUDE.md fresh on each task."
