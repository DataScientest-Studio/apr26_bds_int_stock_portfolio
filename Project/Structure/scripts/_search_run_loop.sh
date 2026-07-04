#!/usr/bin/env bash
# tmux window "run": re-invoke the worker forever (continuous mode has no
# completion condition — only STOP.flag / HALT.flag / search_control.json.halt
# end it). Restarts on any non-halt exit; a crash-storm (>10 restarts inside
# 10 minutes) trips HALT.flag itself so a human looks before it keeps burning
# CPU into the same failure.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."   # Project/Structure/
PY=../.venv/bin/python3
LOG_DIR=logs/search
mkdir -p "$LOG_DIR"

restarts_window=()

while true; do
  [ -f "$LOG_DIR/STOP.flag" ] && { echo "STOP.flag present -> exiting run loop"; break; }
  [ -f "$LOG_DIR/HALT.flag" ] && { echo "HALT.flag present -> exiting run loop"; break; }

  OMP_NUM_THREADS=1 "$PY" feature_search_worker.py 2>&1 | tee -a "$LOG_DIR/worker.log"
  rc=${PIPESTATUS[0]}

  [ "$rc" -eq 3 ] && { echo "worker halted (rc=3) -> exiting run loop"; break; }
  [ -f "$LOG_DIR/STOP.flag" ] && { echo "STOP.flag present -> exiting run loop"; break; }
  [ -f "$LOG_DIR/HALT.flag" ] && { echo "HALT.flag present -> exiting run loop"; break; }

  now=$(date +%s)
  restarts_window+=("$now")
  cutoff=$((now - 600))
  filtered=()
  for t in "${restarts_window[@]}"; do [ "$t" -ge "$cutoff" ] && filtered+=("$t"); done
  restarts_window=("${filtered[@]}")

  if [ "${#restarts_window[@]}" -gt 10 ]; then
    echo "crash-storm: >10 worker restarts in 10 minutes -> HALT.flag (needs a human)" | tee -a "$LOG_DIR/ALERTS.txt"
    touch "$LOG_DIR/HALT.flag"
    break
  fi

  echo "worker exited rc=$rc; resuming in 10s (restarts in last 10min: ${#restarts_window[@]})"
  sleep 10
done
