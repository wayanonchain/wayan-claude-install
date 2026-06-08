#!/usr/bin/env bash
#
# Wayan Claude Agents — post-install verification
#
# Asserts that every expected artifact exists. Exit code 0 = all good.
#
set -uo pipefail

PASS=0
FAIL=0
pass() { printf '\033[1;32mPASS\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
fail() { printf '\033[1;31mFAIL\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }

check_exists()  { [[ -e "$1" ]] && pass "exists: $1" || fail "missing: $1"; }
check_cmd()     { command -v "$1" >/dev/null 2>&1 && pass "command: $1" || fail "no command: $1"; }
check_unit()    { systemctl list-unit-files "$1" 2>/dev/null | grep -q "$1" && pass "unit: $1" || fail "no unit: $1"; }

echo "== Wayan install verification =="

id wayan >/dev/null 2>&1 && pass "user: wayan" || fail "user: wayan"

check_cmd node
check_cmd python3
check_cmd git
check_cmd jq

check_exists /home/wayan/.config
check_exists /home/wayan/.cache
check_exists /home/wayan/.claude
check_exists /home/wayan/.claude-lab/jupiter/CLAUDE.md
check_exists /home/wayan/.claude-lab/jupiter/USER.md
check_exists /home/wayan/.claude-lab/uran/CLAUDE.md
check_exists /home/wayan/.claude-lab/uran/USER.md
check_exists /opt/wayan-jupiter
check_exists /opt/wayan-uran
check_exists /opt/wayan-jupiter/venv/bin/python
check_exists /opt/wayan-uran/venv/bin/python
check_exists /opt/wayan-jupiter/gateway/__main__.py
check_exists /opt/wayan-uran/gateway/__main__.py
check_exists /etc/wayan-jupiter.env
check_exists /etc/wayan-uran.env
check_exists /etc/sudoers.d/wayan-agents

check_unit wayan-jupiter.service
check_unit wayan-uran.service

if [[ -e /etc/sudoers.d/wayan-agents ]]; then
  visudo -cf /etc/sudoers.d/wayan-agents >/dev/null 2>&1 \
    && pass "sudoers valid" || fail "sudoers invalid"
fi

echo
echo "Results: ${PASS} passed, ${FAIL} failed."
[[ "${FAIL}" -eq 0 ]]
