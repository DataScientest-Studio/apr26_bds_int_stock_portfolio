#!/usr/bin/env bash
# Cron entrypoint for the continuous full-universe feature-search loop (S.1).
# Idempotent by construction: make feature-search-loop no-ops when the tmux
# session already runs in universe mode and the supervisor pid is alive, and
# relaunches whatever died otherwise. Safe to call from @reboot and from a
# */N heartbeat — this is the OS-level backstop above the in-process
# supervisor (which itself only survives as long as its own process does).
# Login shell (`bash -lc` in the crontab) provides PATH for make/tmux/git.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."   # Project/Structure/
mkdir -p logs/search
# HALT.flag (human stop) / DONE.flag (universe fully optimized) — never auto-relaunch through either.
[ -f logs/search/HALT.flag ] && { echo "[$(date -u +%FT%TZ)] HALT.flag present — cron stands down"; exit 0; }
[ -f logs/search/DONE.flag ] && { echo "[$(date -u +%FT%TZ)] DONE.flag present (fully optimized) — cron stands down"; exit 0; }
echo "[$(date -u +%FT%TZ)] cron tick -> make feature-search-loop"
make feature-search-loop
