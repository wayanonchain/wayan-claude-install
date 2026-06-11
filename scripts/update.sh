#!/usr/bin/env bash
#
# Wayan Claude Agents — repo-first update
#
# GitHub is the single source of truth (see docs/DEPLOYMENT.md). Default run is
# SAFE: it pulls main, runs the full test suite, and reports gateway drift —
# it changes nothing in production unless you explicitly pass --deploy.
#
# Usage:
#   bash scripts/update.sh                      # pull + tests + drift check (read-only)
#   sudo bash scripts/update.sh --deploy        # ... then deploy-gateway.sh (no restart)
#   sudo bash scripts/update.sh --deploy --restart   # ... deploy + restart + verify
#   sudo bash scripts/update.sh --full          # legacy: re-run install.sh (templates,
#                                               # skills, units; idempotent, no-clobber)
#
set -euo pipefail

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

DEPLOY=false; RESTART=false; FULL=false
for arg in "$@"; do
  case "${arg}" in
    --deploy)  DEPLOY=true ;;
    --restart) RESTART=true ;;
    --full)    FULL=true ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown flag: ${arg} (see --help)" ;;
  esac
done
[[ "${RESTART}" == "true" && "${DEPLOY}" != "true" ]] && die "--restart requires --deploy"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -d "${REPO_ROOT}/.git" ]] || die "not a git checkout: ${REPO_ROOT} — clone the repo first"

# 1) Pull main (fast-forward only; a dirty/diverged tree must be fixed by hand).
log "git pull origin main (--ff-only) ..."
git -C "${REPO_ROOT}" pull --ff-only origin main || die "git pull failed — resolve manually; never edit production directly"
ok "repo at $(git -C "${REPO_ROOT}" rev-parse --short HEAD)"

# 2) Run the full test suite before anything touches production.
PYBIN="python3"
[[ -x /opt/wayan-jupiter/venv/bin/python ]] && PYBIN="/opt/wayan-jupiter/venv/bin/python"
log "Running tests (${PYBIN}) ..."
( cd "${REPO_ROOT}" && PYTHONPATH=src "${PYBIN}" -m unittest discover -s tests ) \
  || die "tests FAILED — fix before deploying; production untouched"
ok "tests green"

# 3) Legacy full path (installer is idempotent and preserves env files).
if [[ "${FULL}" == "true" ]]; then
  [[ "$(id -u)" -eq 0 ]] || die "--full must run as root (use sudo)"
  log "Re-running installer (idempotent) ..."
  bash "${REPO_ROOT}/install.sh"
  log "Restarting services ..."
  systemctl restart wayan-jupiter.service wayan-uran.service
  systemctl is-active wayan-jupiter.service wayan-uran.service
  ok "Full update complete."
  exit 0
fi

# 4) Drift check — read-only.
log "Checking gateway drift ..."
if bash "${REPO_ROOT}/scripts/deploy-gateway.sh" --check; then
  DRIFT=false
else
  DRIFT=true
fi

# 5) Deploy only with the explicit flag; otherwise tell the operator what to run.
if [[ "${DRIFT}" == "true" ]]; then
  if [[ "${DEPLOY}" == "true" ]]; then
    if [[ "${RESTART}" == "true" ]]; then
      bash "${REPO_ROOT}/scripts/deploy-gateway.sh" --restart
    else
      bash "${REPO_ROOT}/scripts/deploy-gateway.sh"
    fi
  else
    warn "Production is BEHIND the repo. Review the drift above, then run:"
    warn "  sudo bash scripts/deploy-gateway.sh --restart"
    warn "(or preview first: sudo bash scripts/deploy-gateway.sh --dry-run)"
    exit 1
  fi
else
  ok "No drift — production matches repo."
fi
