#!/usr/bin/env bash
#
# Wayan Claude Agents — repo-first gateway deploy
#
# GitHub is the single source of truth. This script syncs the repo's
# src/gateway/ into both live agent trees (/opt/wayan-jupiter/gateway and
# /opt/wayan-uran/gateway) with timestamped backups, and NOTHING else:
# it never touches env files, secrets, ov.conf, OpenViking, venvs, workspaces,
# or systemd units. See docs/DEPLOYMENT.md.
#
# Usage:
#   sudo bash scripts/deploy-gateway.sh --check       # drift report only (read-only)
#   sudo bash scripts/deploy-gateway.sh --dry-run     # preview a deploy, change nothing
#   sudo bash scripts/deploy-gateway.sh               # backup + sync (no restart)
#   sudo bash scripts/deploy-gateway.sh --restart     # backup + sync + restart + verify
#   ... --allow-dirty                                 # deploy despite uncommitted changes
#
# Exit codes: 0 = OK / PASS;  1 = drift (--check) or refused;  2 = usage/env error.
#
# Test/dev overrides (used by tests/test_deploy.py; never needed in production):
#   WAYAN_JUPITER_OPT, WAYAN_URAN_OPT   target roots (default /opt/wayan-{jupiter,uran})
#   WAYAN_DEPLOY_REQUIRE_VPS=false      skip Linux/root/systemd/import checks
#   WAYAN_DEPLOY_CHOWN=false            skip chown -R wayan:wayan
#
set -euo pipefail

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit "${2:-2}"; }

WAYAN_USER="wayan"
JUPITER_OPT="${WAYAN_JUPITER_OPT:-/opt/wayan-jupiter}"
URAN_OPT="${WAYAN_URAN_OPT:-/opt/wayan-uran}"
REQUIRE_VPS="${WAYAN_DEPLOY_REQUIRE_VPS:-true}"
DO_CHOWN="${WAYAN_DEPLOY_CHOWN:-true}"
TARGETS=("${JUPITER_OPT}" "${URAN_OPT}")
TARGET_NAMES=("Jupiter" "Uran")
SERVICES=(wayan-jupiter.service wayan-uran.service)

MODE="deploy"
RESTART=false
ALLOW_DIRTY=false
for arg in "$@"; do
  case "${arg}" in
    --check)       MODE="check" ;;
    --dry-run)     MODE="dry-run" ;;
    --restart)     RESTART=true ;;
    --allow-dirty) ALLOW_DIRTY=true ;;
    -h|--help)     grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown flag: ${arg} (see --help)" ;;
  esac
done
[[ "${MODE}" == "check" && "${RESTART}" == "true" ]] && die "--check is read-only; drop --restart"

# ---------------------------------------------------------------- repo root --
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO_ROOT}/src/gateway"
[[ -f "${SRC}/__init__.py" && -f "${SRC}/__main__.py" && -f "${SRC}/app.py" ]] \
  || die "repo root not found: ${SRC} is not the gateway package (run from a repo checkout)"
REPO_VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "${SRC}/__init__.py" | head -1)"

# ----------------------------------------------------------------- git state --
BRANCH="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")"
COMMIT="$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || echo "?")"
DIRTY="$(git -C "${REPO_ROOT}" status --porcelain 2>/dev/null || true)"
[[ "${BRANCH}" == "main" ]] || warn "not on 'main' (branch: ${BRANCH}) — production deploys should come from main"

# ------------------------------------------------------------------ VPS guard --
if [[ "${REQUIRE_VPS}" == "true" ]]; then
  [[ "$(uname -s)" == "Linux" ]] || die "this script runs only on the VPS (Linux). Use --check from anywhere via ssh."
  command -v systemctl >/dev/null 2>&1 || die "systemctl not found — not the Wayan VPS?"
  systemctl cat wayan-jupiter.service >/dev/null 2>&1 \
    || die "wayan-jupiter.service not installed — run install.sh first"
  if [[ "${MODE}" == "deploy" ]]; then
    [[ "$(id -u)" -eq 0 ]] || die "deploy needs root (use sudo); --check and --dry-run work unprivileged"
  fi
fi

# ----------------------------------------------------------------- helpers --
file_hash() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

list_py() {  # sorted relative *.py paths, __pycache__ excluded
  (cd "$1" && find . -name '__pycache__' -prune -o -type f -name '*.py' -print | sed 's|^\./||' | sort)
}

DRIFT_COUNT=0
compare_target() {  # $1 = target gateway dir; prints names only, never contents
  local tgt="$1" f drift=0
  if [[ ! -d "${tgt}" ]]; then
    printf '  ABSENT   %s (whole dir missing)\n' "${tgt}"
    DRIFT_COUNT=$((DRIFT_COUNT + 1)); return 0
  fi
  while IFS= read -r f; do
    [[ -z "${f}" ]] && continue
    if [[ -f "${SRC}/${f}" && -f "${tgt}/${f}" ]]; then
      if [[ "$(file_hash "${SRC}/${f}")" != "$(file_hash "${tgt}/${f}")" ]]; then
        printf '  CHANGED  %s\n' "${f}"; drift=$((drift + 1))
      fi
    elif [[ -f "${SRC}/${f}" ]]; then
      printf '  NEW      %s (in repo, not deployed)\n' "${f}"; drift=$((drift + 1))
    else
      printf '  EXTRA    %s (deployed, not in repo — deploy removes it)\n' "${f}"; drift=$((drift + 1))
    fi
  done < <({ list_py "${SRC}"; list_py "${tgt}"; } | sort -u)
  if [[ ${drift} -eq 0 ]]; then
    printf '  identical (%s files)\n' "$(list_py "${SRC}" | wc -l | tr -d ' ')"
  fi
  DRIFT_COUNT=$((DRIFT_COUNT + drift))
}

report_header() {
  echo "Repo gateway: src/gateway (version ${REPO_VERSION}, branch ${BRANCH}, commit ${COMMIT})"
}

# ------------------------------------------------------------------- check --
if [[ "${MODE}" == "check" ]]; then
  report_header
  for i in 0 1; do
    echo "${TARGET_NAMES[$i]}: ${TARGETS[$i]}/gateway"
    compare_target "${TARGETS[$i]}/gateway"
  done
  if [[ ${DRIFT_COUNT} -eq 0 ]]; then
    echo "Status: PASS, production matches repo"
    exit 0
  fi
  echo "Status: FAIL, drift detected (${DRIFT_COUNT} file(s)) — sync with: sudo bash scripts/deploy-gateway.sh --restart"
  exit 1
fi

# ----------------------------------------------------------------- dry-run --
TS="$(date +%Y%m%d-%H%M%S)"
if [[ "${MODE}" == "dry-run" ]]; then
  log "DRY-RUN — nothing will be changed"
  report_header
  for i in 0 1; do
    echo "${TARGET_NAMES[$i]}: ${TARGETS[$i]}/gateway"
    compare_target "${TARGETS[$i]}/gateway"
    echo "  backup that would be created: ${TARGETS[$i]}/gateway.bak.${TS}"
  done
  if [[ -n "${DIRTY}" && "${ALLOW_DIRTY}" != "true" ]]; then
    warn "working tree is DIRTY — a real deploy would REFUSE (pass --allow-dirty to override)"
  fi
  if [[ "${RESTART}" == "true" ]]; then
    echo "services that would be restarted: ${SERVICES[*]}"
  else
    echo "services that would be restarted: none (pass --restart)"
  fi
  [[ ${DRIFT_COUNT} -eq 0 ]] && ok "nothing to deploy — production already matches repo" \
                             || log "${DRIFT_COUNT} file(s) would be synced"
  exit 0
fi

# ------------------------------------------------------------------ deploy --
if [[ -n "${DIRTY}" && "${ALLOW_DIRTY}" != "true" ]]; then
  die "working tree is dirty — commit/push first (repo is the source of truth), or pass --allow-dirty" 1
fi

report_header
log "Pre-deploy drift:"
for i in 0 1; do
  echo "${TARGET_NAMES[$i]}: ${TARGETS[$i]}/gateway"
  compare_target "${TARGETS[$i]}/gateway"
done
if [[ ${DRIFT_COUNT} -eq 0 ]]; then
  ok "production already matches repo — nothing to deploy"
  [[ "${RESTART}" != "true" ]] && exit 0
fi

BACKUPS=()
for i in 0 1; do
  root="${TARGETS[$i]}"
  tgt="${root}/gateway"
  [[ -d "${root}" ]] || die "target root missing: ${root} (run install.sh first)"

  # Backup (only if something is there to back up).
  bak="(no previous gateway dir — nothing was backed up)"
  if [[ -d "${tgt}" ]]; then
    bak="${tgt}.bak.${TS}"
    cp -a "${tgt}" "${bak}"
    BACKUPS+=("${bak}")
    ok "backup: ${bak}"
  fi

  # Stage, sanitize, then swap — the only paths ever written are
  # <root>/gateway and <root>/.gateway.staged.*; env files, secrets and
  # OpenViking config are untouched by construction.
  staged="${root}/.gateway.staged.$$"
  rm -rf "${staged}"
  cp -R "${SRC}" "${staged}"
  find "${staged}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  if [[ -n "$(find "${staged}" \( -name '*.env' -o -name 'ov.conf' -o -name '*credential*' -o -name '*.pem' -o -name 'id_*' \) -print -quit)" ]]; then
    rm -rf "${staged}"
    die "refusing to deploy: secret-shaped file found inside src/gateway (names withheld) — clean the repo first" 1
  fi
  if [[ "${DO_CHOWN}" == "true" ]]; then
    chown -R "${WAYAN_USER}:${WAYAN_USER}" "${staged}"
  fi
  rm -rf "${tgt}"
  mv "${staged}" "${tgt}"
  ok "deployed: ${tgt}"

  # Import sanity check against the agent's own venv (real VPS only).
  if [[ "${REQUIRE_VPS}" == "true" && -x "${root}/venv/bin/python" ]]; then
    if sudo -u "${WAYAN_USER}" bash -c "cd '${root}' && '${root}/venv/bin/python' -c 'import gateway'" >/dev/null 2>&1; then
      ok "import check OK (${root})"
    else
      die "gateway import FAILED in ${root} — roll back: rm -rf '${tgt}' && mv '${bak}' '${tgt}'" 1
    fi
  fi
done

# ------------------------------------------------------------------ restart --
if [[ "${RESTART}" == "true" ]]; then
  log "Restarting services ..."
  systemctl restart "${SERVICES[@]}"
  sleep 3
  for svc in "${SERVICES[@]}"; do
    state="$(systemctl is-active "${svc}" 2>/dev/null || true)"
    if [[ "${state}" == "active" ]]; then ok "${svc}: active"
    else die "${svc} is '${state}' after restart — inspect: journalctl -u ${svc} -n 50; roll back from ${TARGETS[0]}/gateway.bak.${TS}" 1
    fi
  done
else
  warn "services NOT restarted — old code is still running. Apply with: sudo systemctl restart ${SERVICES[*]}"
fi

# ------------------------------------------------------------- final report --
log "Post-deploy verification:"
DRIFT_COUNT=0
for i in 0 1; do
  echo "${TARGET_NAMES[$i]}: ${TARGETS[$i]}/gateway"
  compare_target "${TARGETS[$i]}/gateway"
done
[[ ${DRIFT_COUNT} -eq 0 ]] || die "post-deploy drift remains (${DRIFT_COUNT} file(s)) — investigate before trusting production" 1
if [[ ${#BACKUPS[@]} -gt 0 ]]; then
  log "Backups (rollback: rm -rf <opt>/gateway && mv <backup> <opt>/gateway && systemctl restart <svc>):"
  for b in "${BACKUPS[@]}"; do echo "  ${b}"; done
fi
ok "Status: PASS, production matches repo (gateway ${REPO_VERSION})"
