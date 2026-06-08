#!/usr/bin/env bash
#
# Wayan Claude Agents — full uninstall
#
# Removes EVERYTHING this installer created: services, env, /opt dirs,
# sudoers, the .claude-lab workspaces, and the 'wayan' user IF (and only if)
# it was created by this installer.
#
set -euo pipefail

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

WAYAN_USER="wayan"
WAYAN_HOME="/home/${WAYAN_USER}"
LAB_DIR="${WAYAN_HOME}/.claude-lab"
MARKER="${LAB_DIR}/.created_by_wayan_installer"

[[ "$(id -u)" -eq 0 ]] || die "uninstall.sh must run as root (use sudo)."

printf '\033[1;33mThis will completely remove Wayan agents, workspaces, and config.\033[0m\n'
printf 'Type DELETE to remove Wayan agents completely: '
read -r CONFIRM
[[ "${CONFIRM}" == "DELETE" ]] || die "Aborted (you did not type DELETE)."

log "Stopping and disabling services ..."
systemctl stop wayan-jupiter.service 2>/dev/null || true
systemctl stop wayan-uran.service    2>/dev/null || true
systemctl disable wayan-jupiter.service 2>/dev/null || true
systemctl disable wayan-uran.service    2>/dev/null || true

log "Removing unit files, env, sudoers, /opt dirs ..."
rm -f /etc/systemd/system/wayan-jupiter.service
rm -f /etc/systemd/system/wayan-uran.service
rm -f /etc/wayan-jupiter.env
rm -f /etc/wayan-uran.env
rm -f /etc/sudoers.d/wayan-agents
rm -rf /opt/wayan-jupiter
rm -rf /opt/wayan-uran
systemctl daemon-reload

# Decide whether to remove the user (only if we created it).
USER_WAS_OURS=0
[[ -f "${MARKER}" ]] && USER_WAS_OURS=1

log "Removing workspaces (${LAB_DIR}) ..."
rm -rf "${LAB_DIR}"

if id "${WAYAN_USER}" >/dev/null 2>&1; then
  if [[ "${USER_WAS_OURS}" -eq 1 ]]; then
    log "User '${WAYAN_USER}' was created by this installer; removing it and ${WAYAN_HOME} ..."
    pkill -u "${WAYAN_USER}" 2>/dev/null || true
    userdel --remove "${WAYAN_USER}" 2>/dev/null || warn "userdel failed; remove '${WAYAN_USER}' manually."
    ok "User '${WAYAN_USER}' removed."
  else
    warn "User '${WAYAN_USER}' was NOT created by this installer — leaving it untouched."
  fi
fi

ok "Uninstall complete."
