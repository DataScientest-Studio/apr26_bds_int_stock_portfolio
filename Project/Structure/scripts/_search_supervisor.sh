#!/usr/bin/env bash
# Outer self-healer: survives the whole tmux session dying (not just the
# worker process). Polls forever (continuous mode); relaunches search_on.sh
# if the session is gone or the "run" pane died, bounded by MAX_RESTARTS so a
# truly broken environment stops paging instead of looping silently forever.
# Never kills by process name (pkill -f self-match is a known trap) — this
# script only starts sessions and reads tmux/flag state.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."   # Project/Structure/

SESSION=liora_feature_search
LOG_DIR=logs/search
HALT_FLAG="$LOG_DIR/HALT.flag"
STOP_FLAG="$LOG_DIR/STOP.flag"
MAX_RESTARTS=10
restarts=0

mkdir -p "$LOG_DIR"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "supervisor up (pid $$)"

while true; do
  if [ -f "$HALT_FLAG" ]; then
    log "HALT.flag present -> supervisor stopping"
    exit 1
  fi
  if [ -f "$STOP_FLAG" ]; then
    log "STOP.flag present -> supervisor stopping gracefully"
    exit 0
  fi

  if tmux has-session -t "$SESSION" 2>/dev/null; then
    dead=$(tmux list-panes -t "$SESSION:run" -F '#{pane_dead}' 2>/dev/null | head -1)
    if [ "$dead" = "1" ]; then
      log "run pane DEAD -> killing session, will relaunch"
      tmux kill-session -t "$SESSION" 2>/dev/null || true
    else
      sleep 60
      continue
    fi
  else
    log "tmux session GONE -> relaunching"
  fi

  if [ "$restarts" -ge "$MAX_RESTARTS" ]; then
    log "max restarts ($MAX_RESTARTS) reached -> touching HALT.flag, giving up"
    touch "$HALT_FLAG"
    exit 2
  fi
  restarts=$((restarts + 1))
  bash scripts/search_on.sh || log "search_on.sh exited non-zero (attempt $restarts/$MAX_RESTARTS)"
  sleep 30
done
