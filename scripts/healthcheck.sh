#!/usr/bin/env bash
#
# Wayan Claude Agents — healthcheck
#
# Prints the state of every moving part. Read-only; safe to run any time.
#
set -uo pipefail

hdr()  { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
bad()  { printf '\033[1;31m[x]\033[0m %s\n' "$*"; }

WAYAN_USER="wayan"
LAB_DIR="/home/${WAYAN_USER}/.claude-lab"
SUDOERS_FILE="/etc/sudoers.d/wayan-agents"

hdr "User"
if id "${WAYAN_USER}" >/dev/null 2>&1; then id "${WAYAN_USER}"; ok "user present"; else bad "user '${WAYAN_USER}' missing"; fi

hdr "Runtimes"
node -v          2>/dev/null && ok "node ok"            || bad "node missing"
python3 --version 2>/dev/null && ok "python3 ok"         || bad "python3 missing"
if id "${WAYAN_USER}" >/dev/null 2>&1; then
  sudo -u "${WAYAN_USER}" bash -lc 'claude --version' 2>/dev/null && ok "claude ok" \
    || bad "claude not found for ${WAYAN_USER} (login may be pending)"
fi

hdr "Services"
systemctl --no-pager --full status wayan-jupiter.service 2>/dev/null || bad "wayan-jupiter not loaded"
systemctl --no-pager --full status wayan-uran.service    2>/dev/null || bad "wayan-uran not loaded"

hdr "Workspaces"
ls -la "${LAB_DIR}" 2>/dev/null || bad "${LAB_DIR} missing"

hdr "Env files"
ls -la /etc/wayan-jupiter.env /etc/wayan-uran.env 2>/dev/null || bad "env files missing"

hdr "Sudoers"
ls -la "${SUDOERS_FILE}" 2>/dev/null && visudo -cf "${SUDOERS_FILE}" 2>/dev/null \
  && ok "sudoers valid" || bad "sudoers missing/invalid"

printf '\n'
