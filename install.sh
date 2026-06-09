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
  # Home dirs referenced by the services' ReadWritePaths MUST exist before the
  # units can start, or systemd fails namespace setup. Claude also writes its
  # auth/state/cache here once 'wayan' logs in.
  install -d -m 0700 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${WAYAN_HOME}/.config"
  install -d -m 0700 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${WAYAN_HOME}/.cache"
  install -d -m 0700 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${WAYAN_HOME}/.claude"
  ok "Workspaces ready: ${JUPITER_WS}, ${URAN_WS}"
  ok "Home dirs ready: ${WAYAN_HOME}/.config, ${WAYAN_HOME}/.cache, ${WAYAN_HOME}/.claude"
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
# 8b. Skills (read-only playbooks) + logs dirs, copied into each workspace.
#     Skill files are NOT overwritten if the user has edited them (cp -n).
# ----------------------------------------------------------------------------
deploy_skills() {
  log "Deploying skills + logs into workspaces ..."
  local ws
  for ws in "${JUPITER_WS}" "${URAN_WS}"; do
    install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${ws}/skills"
    # -n = never overwrite an existing (possibly user-edited) skill file.
    cp -rn "${SRC_DIR}/skills/." "${ws}/skills/" 2>/dev/null || true
    install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${ws}/logs/successful"
    install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${ws}/logs/failed"
    [[ -f "${SRC_DIR}/logs/README.md" ]] && cp -n "${SRC_DIR}/logs/README.md" "${ws}/logs/README.md" 2>/dev/null || true
    chown -R "${WAYAN_USER}:${WAYAN_USER}" "${ws}/skills" "${ws}/logs"
    ok "skills + logs ready in ${ws}"
  done
}

# ----------------------------------------------------------------------------
# 8c. Day 2 orchestration layer (rules, learnings, memory, mapping, skill-lab).
#     Copied into each workspace no-clobber; user-edited files are preserved.
# ----------------------------------------------------------------------------
deploy_orchestration() {
  log "Deploying orchestration layer into workspaces ..."
  local ws
  for ws in "${JUPITER_WS}" "${URAN_WS}"; do
    install -d -m 0750 -o "${WAYAN_USER}" -g "${WAYAN_USER}" "${ws}/orchestration"
    # -n = never overwrite an existing (possibly user-edited) orchestration file.
    cp -rn "${SRC_DIR}/orchestration/." "${ws}/orchestration/" 2>/dev/null || true
    chown -R "${WAYAN_USER}:${WAYAN_USER}" "${ws}/orchestration"
    ok "orchestration ready in ${ws}"
  done
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
  # Per-agent default permission mode for headless `claude -p` (no TTY).
  # Initial deployment: both agents use acceptEdits. Uran can be switched to
  # bypassPermissions manually (edit /etc/wayan-uran.env) after VPS validation.
  local perm_mode
  case "${agent}" in
    jupiter) perm_mode="acceptEdits" ;;
    uran)    perm_mode="acceptEdits" ;;
    *)       perm_mode="" ;;
  esac

  log "Creating ${path} ..."
  cat > "${path}" <<EOF
# Environment for Wayan ${agent} agent (read by the Telegram gateway via systemd)
# After editing: systemctl restart wayan-${agent}.service

# --- required ---
TELEGRAM_BOT_TOKEN=
WAYAN_AGENT=${agent}
WAYAN_WORKSPACE=${LAB_DIR}/${agent}

# --- optional (sane defaults applied by the gateway if left blank) ---
# Comma-separated Telegram chat IDs allowed to talk to this agent. Empty = allow all.
TELEGRAM_ALLOWED_CHAT_IDS=
# Path to the claude binary if it is not on PATH.
CLAUDE_BIN=claude
# Seconds to wait for a claude response before giving up.
CLAUDE_TIMEOUT=300
# Continue the conversation within a running process (true/false).
CLAUDE_CONTINUE=true
# Claude permission mode for headless runs: default | acceptEdits | bypassPermissions | plan
# (headless agents with no TTY usually need acceptEdits or bypassPermissions to use tools)
CLAUDE_PERMISSION_MODE=${perm_mode}
# Telegram long-poll timeout (seconds).
TELEGRAM_POLL_TIMEOUT=50
# Log level: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO

# --- voice input (Groq Whisper) — v1.1.0 ---
# Get a key at https://console.groq.com . Leave blank to disable voice.
GROQ_API_KEY=
# Master voice switch and direction toggles. Output (TTS) is not implemented yet.
VOICE_ENABLED=true
VOICE_INPUT=true
VOICE_OUTPUT=false
# Groq transcription model.
GROQ_MODEL=whisper-large-v3-turbo
# Seconds to wait for a transcription before giving up.
VOICE_TIMEOUT=120

# --- file attachments (documents / photos) — v1.1.0 ---
# Downloaded into <workspace>/uploads and passed to Claude by path.
FILES_ENABLED=true
# Reject attachments larger than this (Telegram Bot API caps downloads at 20 MB).
FILE_MAX_MB=20
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
# 10. Verify service-required directories exist BEFORE the units are installed
#     (systemd ReadWritePaths fails namespace setup if any are missing).
# ----------------------------------------------------------------------------
verify_service_dirs() {
  log "Verifying directories required by the services ..."
  local missing=0 d
  for d in "${WAYAN_HOME}/.config" "${WAYAN_HOME}/.cache" "${WAYAN_HOME}/.claude" \
           "${LAB_DIR}" "${JUPITER_OPT}" "${URAN_OPT}"; do
    if [[ -d "${d}" ]]; then
      ok "present: ${d}"
    else
      err "missing: ${d}"
      missing=1
    fi
  done
  [[ "${missing}" -eq 0 ]] || die "required directories missing; aborting before services are installed."
}

# ----------------------------------------------------------------------------
# 11. systemd services
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
# 12. Deploy the gateway code + Python venv into each /opt dir
# ----------------------------------------------------------------------------
deploy_agent_code() {
  local opt="$1"
  log "Deploying gateway to ${opt} ..."

  # Ship the latest code each run (this is our code, not user data, so replace it).
  rm -rf "${opt}/gateway"
  cp -r "${SRC_DIR}/src/gateway" "${opt}/gateway"
  cp "${SRC_DIR}/requirements.txt" "${opt}/requirements.txt"
  chown -R "${WAYAN_USER}:${WAYAN_USER}" "${opt}/gateway" "${opt}/requirements.txt"

  # Create the venv once; reuse it on subsequent runs.
  if [[ ! -x "${opt}/venv/bin/python" ]]; then
    log "Creating virtualenv at ${opt}/venv ..."
    sudo -u "${WAYAN_USER}" python3 -m venv "${opt}/venv"
  fi

  log "Installing Python dependencies into ${opt}/venv ..."
  sudo -u "${WAYAN_USER}" "${opt}/venv/bin/pip" install --quiet --upgrade pip
  sudo -u "${WAYAN_USER}" "${opt}/venv/bin/pip" install --quiet -r "${opt}/requirements.txt"

  # Sanity check: the entrypoint must import cleanly with the venv interpreter.
  if sudo -u "${WAYAN_USER}" bash -lc "cd '${opt}' && '${opt}/venv/bin/python' -c 'import gateway' >/dev/null 2>&1"; then
    ok "Gateway deployed to ${opt} (venv + deps verified)."
  else
    die "Gateway import failed in ${opt}; check ${opt}/gateway and the venv."
  fi
}

deploy_gateway() {
  deploy_agent_code "${JUPITER_OPT}"
  deploy_agent_code "${URAN_OPT}"
}

# ----------------------------------------------------------------------------
# 13. Claude login gate — agents cannot talk to Claude until 'wayan' has logged in
# ----------------------------------------------------------------------------
CLAUDE_LOGGED_IN=0

check_claude_login() {
  log "Checking Claude Code login for '${WAYAN_USER}' ..."
  if sudo -u "${WAYAN_USER}" bash -lc '
        test -f "$HOME/.claude/.credentials.json" ||
        test -f "$HOME/.config/claude/.credentials.json" ||
        { test -f "$HOME/.claude.json" && grep -qi "oauthAccount\|\"account\"" "$HOME/.claude.json"; }
      ' 2>/dev/null; then
    CLAUDE_LOGGED_IN=1
    ok "Claude Code appears to be logged in for ${WAYAN_USER}."
  else
    CLAUDE_LOGGED_IN=0
    warn "Claude Code is NOT logged in for ${WAYAN_USER}."
    warn "Do not start the services yet — agents will error on every message until login."
    warn "Log in with:  sudo -u ${WAYAN_USER} -i   then run:  claude"
  fi
}

# ----------------------------------------------------------------------------
# 14. Final banner
# ----------------------------------------------------------------------------
final_banner() {
  cat <<EOF

\033[1;32m============================================================\033[0m
 Wayan Claude Agents — installation complete
\033[1;32m============================================================\033[0m

 INSTALLED
   - Node.js $(node -v 2>/dev/null || echo '?')  /  npm $(npm -v 2>/dev/null || echo '?')
   - python3 $(python3 --version 2>/dev/null | awk '{print $2}')
   - Claude Code (per user '${WAYAN_USER}')  —  login: $( [[ "${CLAUDE_LOGGED_IN}" -eq 1 ]] && echo 'OK' || echo 'REQUIRED (see NEXT STEPS)' )
   - Gateway venv + deps: ${JUPITER_OPT}/venv, ${URAN_OPT}/venv
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
  deploy_skills
  deploy_orchestration
  create_env_files
  deploy_gateway
  verify_service_dirs
  install_services
  install_sudoers
  check_claude_login
  printf '%b' "$(final_banner)\n"
}

main "$@"
