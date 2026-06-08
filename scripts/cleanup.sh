#!/usr/bin/env bash
#
# Wayan Claude Agents — cleanup
#
# Safely removes a previous installation so install.sh can run fresh.
# Does NOT remove the 'wayan' user or /home/wayan (use uninstall.sh for that).
#
set -euo pipefail

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "cleanup.sh must run as root (use sudo)."

log "Stopping services ..."
systemctl stop wayan-jupiter.service 2>/dev/null || true
systemctl stop wayan-uran.service    2>/dev/null || true

log "Disabling services ..."
systemctl disable wayan-jupiter.service 2>/dev/null || true
systemctl disable wayan-uran.service    2>/dev/null || true

log "Removing unit files, env, sudoers ..."
rm -f /etc/systemd/system/wayan-jupiter.service
rm -f /etc/systemd/system/wayan-uran.service
rm -f /etc/wayan-jupiter.env
rm -f /etc/wayan-uran.env
rm -f /etc/sudoers.d/wayan-agents

log "Removing /opt directories ..."
rm -rf /opt/wayan-jupiter
rm -rf /opt/wayan-uran

systemctl daemon-reload
ok "Cleanup complete. User 'wayan' and /home/wayan were kept."
ok "Workspaces under /home/wayan/.claude-lab were kept (run uninstall.sh to remove)."
