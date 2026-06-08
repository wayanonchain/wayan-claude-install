#!/usr/bin/env bash
#
# Wayan Claude Agents — installer (EdgeLab Day 1 methodology)
#
# Installs two Claude Code agents on an Ubuntu VPS:
#   - Jupiter : main daily agent (code, Telegram, projects)
#   - Uran    : backup/root-fix agent (repairs Jupiter, systemd, VPS)
#
# Idempotent: safe to run multiple times.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/wayanonchain/wayan-claude-install/main/install.sh | sudo bash
# or:
#   git clone https://github.com/wayanonchain/wayan-claude-install.git
#   cd wayan-claude-install && sudo ./install.sh
#
set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
REPO_URL="https://github.com/wayanonchain/wayan-claude-install.git"
WAYAN_USER="wayan"
WAYAN_HOME="/home/${WAYAN_USER}"
LAB_DIR="${WAYAN_HOME}/.claude-lab"
NODE_MAJOR=22

JUPITER_WS="${LAB_DIR}/jupiter"
URAN_WS="${LAB_DIR}/uran"
JUPITER_OPT="/opt/wayan-jupiter"
URAN_OPT="/opt/wayan-uran"

JUPITER_ENV="/etc/wayan-jupiter.env"
URAN_ENV="/etc/wayan-uran.env"
SUDOERS_FILE="/etc/sudoers.d/wayan-agents"

JUPITER_SERVICE="/etc/systemd/system/wayan-jupiter.service"
URAN_SERVICE="/etc/systemd/system/wayan-uran.service"

# ----------------------------------------------------------------------------
# Logging helpers
# ----------------------------------------------------------------------------
log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

# ----------------------------------------------------------------------------
# 1. Must run as root
# ----------------------------------------------------------------------------
require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    die "This installer must run as root. Try: sudo bash install.sh"
  fi
  ok "Running as root."
}

# ----------------------------------------------------------------------------
# 2. Verify Ubuntu 22.04 / 24.04
# ----------------------------------------------------------------------------
require_ubuntu() {
  [[ -r /etc/os-release ]] || die "/etc/os-release not found; unsupported OS."
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    die "Unsupported OS: ${PRETTY_NAME:-unknown}. Ubuntu 22.04 or 24.04 required."
  fi
  case "${VERSION_ID:-}" in
    22.04|24.04) ok "Detected ${PRETTY_NAME}." ;;
    *) die "Unsupported Ubuntu ${VERSION_ID:-?}. Only 22.04 and 24.04 are supported." ;;
  esac
}

# ----------------------------------------------------------------------------
# Locate repo sources (templates/ + systemd/). Clone if running via curl|bash.
# ----------------------------------------------------------------------------
SRC_DIR=""
CLONED_TMP=""

resolve_sources() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"

  if [[ -n "${script_dir}" && -d "${script_dir}/templates" && -d "${script_dir}/systemd" ]]; then
    SRC_DIR="${script_dir}"
    ok "Using local repository sources at ${SRC_DIR}."
    return
  fi

  log "Running without local repo (curl|bash). Cloning ${REPO_URL} ..."
  CLONED_TMP="$(mktemp -d /tmp/wayan-install.XXXXXX)"
  git clone --depth 1 "${REPO_URL}" "${CLONED_TMP}" >/dev/null 2>&1 \
    || die "Failed to clone ${REPO_URL}. Check the URL / network."
  SRC_DIR="${CLONED_TMP}"
  ok "Cloned repository to ${SRC_DIR}."
}

cleanup_tmp() {
  [[ -n "${CLONED_TMP}" && -d "${CLONED_TMP}" ]] && rm -rf "${CLONED_TMP}"
}
trap cleanup_tmp EXIT

# ----------------------------------------------------------------------------
# 3. Base packages
# ----------------------------------------------------------------------------
install_packages() {
  log "Installing base packages ..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y \
    curl git jq build-essential \
    python3 python3-venv python3-pip \
    ca-certificates gnupg
  ok "Base packages installed."
}

# ----------------------------------------------------------------------------
# 4. Node.js 22 (only if missing or wrong major)
# ----------------------------------------------------------------------------
install_node() {
  local current_major=""
  if command -v node >/dev/null 2>&1; then
    current_major="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')"
  fi

  if [[ "${current_major}" == "${NODE_MAJOR}" ]]; then
    ok "Node.js $(node -v) already present."
    return
  fi

  log "Installing Node.js ${NODE_MAJOR}.x via NodeSource ..."
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
  apt-get install -y nodejs
  ok "Node.js $(node -v) installed (npm $(npm -v))."
}

# ----------------------------------------------------------------------------
# 6. Create user wayan (before Claude install so we can install per-user)
# ----------------------------------------------------------------------------
WAYAN_CREATED_BY_INSTALLER=0

create_user() {
  if id "${WAYAN_USER}" >/dev/null 2>&1; then
    ok "User '${WAYAN_USER}' already exists."
  else
    log "Creating user '${WAYAN_USER}' ..."
    useradd --create-home --shell /bin/bash "${WAYAN_USER}"
    WAYAN_CREATED_BY_INSTALLER=1
    ok "User '${WAYAN_USER}' created."
  fi
  # Marker so uninstall knows whether it's safe to delete the user.
  if [[ "${WAYAN_CREATED_BY_INSTALLER}" -eq 1 ]]; then
    install -d -m 0700 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${LAB_DIR}"
    : > "${LAB_DIR}/.created_by_wayan_installer"
    chown "${WAYAN_USER}:${WAYAN_USER}" "${LAB_DIR}/.created_by_wayan_installer"
  fi
}

# ----------------------------------------------------------------------------
# 5. Claude Code (installed as the wayan user)
# ----------------------------------------------------------------------------
install_claude() {
  if sudo -u "${WAYAN_USER}" bash -lc 'command -v claude >/dev/null 2>&1'; then
    ok "Claude Code already installed for ${WAYAN_USER} ($(sudo -u "${WAYAN_USER}" bash -lc 'claude --version' 2>/dev/null || echo '?'))."
    return
  fi
  log "Installing Claude Code for user '${WAYAN_USER}' ..."
  sudo -u "${WAYAN_USER}" bash -lc 'curl -fsSL https://claude.ai/install.sh | bash' \
    || warn "Claude Code install script returned non-zero; verify manually with: sudo -u ${WAYAN_USER} claude --version"
  ok "Claude Code install step finished."
}

# ----------------------------------------------------------------------------
# 7. Directories
# ----------------------------------------------------------------------------
create_dirs() {
  log "Creating directories ..."
  install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${LAB_DIR}"
  install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${JUPITER_WS}"
  install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${URAN_WS}"
  install -d -m 0755 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${JUPITER_OPT}"
  install -d -m 0755 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${URAN_OPT}"
  ok "Workspaces ready: ${JUPITER_WS}, ${URAN_WS}"
}

# ----------------------------------------------------------------------------
# 8. Copy templates (idempotent: don't clobber user-edited files)
# ----------------------------------------------------------------------------
copy_template() {
  local src="$1" dst="$2"
  if [[ -f "${dst}" ]]; then
    ok "Keeping existing ${dst} (not overwritten)."
    return
  fi
  install -m 0640 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${src}" "${dst}"
  ok "Installed ${dst}"
}

copy_templates() {
  log "Copying agent templates ..."
  copy_template "${SRC_DIR}/templates/jupiter/CLAUDE.md" "${JUPITER_WS}/CLAUDE.md"
  copy_template "${SRC_DIR}/templates/jupiter/USER.md"  "${JUPITER_WS}/USER.md"
  copy_template "${SRC_DIR}/templates/uran/CLAUDE.md"   "${URAN_WS}/CLAUDE.md"
  copy_template "${SRC_DIR}/templates/uran/USER.md"     "${URAN_WS}/USER.md"
}

# ----------------------------------------------------------------------------
# 9. Env files (created once; never overwritten so secrets survive)
# ----------------------------------------------------------------------------
create_env_file() {
  local path="$1" agent="$2"
  if [[ -f "${path}" ]]; then
    ok "Keeping existing ${path}."
    return
  fi
  log "Creating ${path} ..."
  cat > "${path}" <<EOF
# Environment for Wayan ${agent} agent
# Fill in the Telegram bot token, then: systemctl restart wayan-$(echo "${agent}" | tr '[:upper:]' '[:lower:]').service
TELEGRAM_BOT_TOKEN=
WAYAN_AGENT=${agent}
WAYAN_WORKSPACE=${LAB_DIR}/$(echo "${agent}" | tr '[:upper:]' '[:lower:]')
EOF
  chown root:"${WAYAN_USER}" "${path}"
  chmod 0640 "${path}"
  ok "Created ${path} (set TELEGRAM_BOT_TOKEN inside)."
}

create_env_files() {
  create_env_file "${JUPITER_ENV}" "jupiter"
  create_env_file "${URAN_ENV}"    "uran"
}

# ----------------------------------------------------------------------------
# 10. systemd services
# ----------------------------------------------------------------------------
install_services() {
  log "Installing systemd services ..."
  install -m 0644 "${SRC_DIR}/systemd/wayan-jupiter.service" "${JUPITER_SERVICE}"
  install -m 0644 "${SRC_DIR}/systemd/wayan-uran.service"    "${URAN_SERVICE}"
  systemctl daemon-reload
  systemctl enable wayan-jupiter.service >/dev/null 2>&1 || true
  systemctl enable wayan-uran.service    >/dev/null 2>&1 || true
  ok "Services installed and enabled (start them after Claude login)."
}

# ----------------------------------------------------------------------------
# 11. sudoers for the wayan user (Uran needs to manage the services)
# ----------------------------------------------------------------------------
install_sudoers() {
  log "Installing sudoers rules ..."
  cat > "${SUDOERS_FILE}" <<EOF
# Wayan agents — limited sudo so Uran can repair/restart Jupiter and inspect logs.
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/systemctl restart wayan-jupiter.service
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/systemctl restart wayan-uran.service
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/systemctl stop wayan-jupiter.service
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/systemctl start wayan-jupiter.service
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/systemctl status wayan-jupiter.service
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/systemctl status wayan-uran.service
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/journalctl -u wayan-jupiter.service *
${WAYAN_USER} ALL=(root) NOPASSWD: /bin/journalctl -u wayan-uran.service *
EOF
  chmod 0440 "${SUDOERS_FILE}"
  if visudo -cf "${SUDOERS_FILE}" >/dev/null 2>&1; then
    ok "sudoers file ${SUDOERS_FILE} validated."
  else
    rm -f "${SUDOERS_FILE}"
    die "sudoers validation failed; removed ${SUDOERS_FILE} to avoid breaking sudo."
  fi
}

# ----------------------------------------------------------------------------
# 12. Final banner
# ----------------------------------------------------------------------------
final_banner() {
  cat <<EOF

\033[1;32m============================================================\033[0m
 Wayan Claude Agents — installation complete
\033[1;32m============================================================\033[0m

 INSTALLED
   - Node.js $(node -v 2>/dev/null || echo '?')  /  npm $(npm -v 2>/dev/null || echo '?')
   - python3 $(python3 --version 2>/dev/null | awk '{print $2}')
   - Claude Code (per user '${WAYAN_USER}')
   - User: ${WAYAN_USER}

 SERVICES (enabled, start after Claude login)
   - wayan-jupiter.service   (main agent)
   - wayan-uran.service      (backup / root-fix agent)

 WORKSPACES
   - Jupiter: ${JUPITER_WS}
   - Uran:    ${URAN_WS}
   - opt:     ${JUPITER_OPT}, ${URAN_OPT}

 CONFIG
   - ${JUPITER_ENV}   (set TELEGRAM_BOT_TOKEN)
   - ${URAN_ENV}      (set TELEGRAM_BOT_TOKEN)
   - ${SUDOERS_FILE}

 NEXT STEPS
   1. Log in to Claude Code as the wayan user:
        sudo -u ${WAYAN_USER} -i
        claude   # complete the browser/login flow
   2. Put Telegram tokens into the env files:
        sudoedit ${JUPITER_ENV}
        sudoedit ${URAN_ENV}
   3. Start the agents:
        systemctl start wayan-jupiter.service
        systemctl start wayan-uran.service

 CHECK
   - Healthcheck:  sudo bash scripts/healthcheck.sh
   - Verify tests: sudo bash tests/verify.sh
   - Logs:         journalctl -u wayan-jupiter.service -f
                   journalctl -u wayan-uran.service -f

\033[1;32m============================================================\033[0m
EOF
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
main() {
  require_root
  require_ubuntu
  resolve_sources
  install_packages
  install_node
  create_user
  install_claude
  create_dirs
  copy_templates
  create_env_files
  install_services
  install_sudoers
  printf '%b' "$(final_banner)\n"
}

main "$@"
