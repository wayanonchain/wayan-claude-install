#!/usr/bin/env bash
#
# Wayan Claude Agents — temporary uploads cleanup (minimal-storage policy).
#
# Deletes files older than FILE_RETENTION_HOURS from each agent's uploads/tmp.
# It NEVER touches transcripts, memory, rules, skills, learnings, mapping, env
# files, or Claude credentials — only uploads/tmp regular files by age.
#
# Usage:
#   bash scripts/cleanup-uploads.sh
#   FILE_RETENTION_HOURS=48 bash scripts/cleanup-uploads.sh
#   WAYAN_LAB_DIR=/path/to/lab bash scripts/cleanup-uploads.sh   # (testing)
#
set -euo pipefail

LAB_DIR="${WAYAN_LAB_DIR:-/home/wayan/.claude-lab}"
RETENTION_HOURS="${FILE_RETENTION_HOURS:-24}"
AGENTS=(jupiter uran)

# find uses minutes; clamp to >= 0.
MINS=$(( RETENTION_HOURS * 60 ))
[ "${MINS}" -ge 0 ] 2>/dev/null || MINS=1440

log() { printf '[cleanup] %s\n' "$*"; }

total=0
for agent in "${AGENTS[@]}"; do
  tmp="${LAB_DIR}/${agent}/uploads/tmp"
  [ -d "${tmp}" ] || { log "skip (no uploads/tmp): ${agent}"; continue; }

  before=$(find "${tmp}" -type f 2>/dev/null | wc -l | tr -d ' ')
  # ONLY regular files, ONLY under uploads/tmp, ONLY older than retention.
  find "${tmp}" -type f -mmin "+${MINS}" -delete 2>/dev/null || true
  after=$(find "${tmp}" -type f 2>/dev/null | wc -l | tr -d ' ')
  removed=$(( before - after ))
  total=$(( total + removed ))
  log "${agent}: removed ${removed} file(s) from uploads/tmp older than ${RETENTION_HOURS}h"
done

log "done — removed ${total} file(s) total."
log "Preserved: transcripts/, memory/, rules/, skills/, learnings/, mapping/, env, credentials."
