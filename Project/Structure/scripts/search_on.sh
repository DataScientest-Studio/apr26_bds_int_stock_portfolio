#!/usr/bin/env bash
# Create (or no-op if present) the detached tmux session running the
# continuous feature-search loop (S.1): windows "run" (worker resume-loop)
# and "watch" (stall watchdog). This script ONLY manages the tmux session —
# it does NOT start the outer supervisor (scripts/_search_supervisor.sh calls
# this script to relaunch the session after a crash; if this script also
# spawned a supervisor, every relaunch would fork a duplicate one). The
# supervisor itself is started once by `make search-on`.
# Usage: scripts/search_on.sh   (run from Project/Structure/)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."   # Project/Structure/

SESSION=liora_feature_search
LOG_DIR=logs/search
PY=../.venv/bin/python3

command -v tmux >/dev/null || { echo "tmux not found"; exit 1; }
[ -x "$PY" ] || { echo "$PY not found — run 'make deps' first"; exit 1; }

if [ -f "$LOG_DIR/HALT.flag" ]; then
  echo "HALT.flag present at $LOG_DIR/HALT.flag — inspect logs, then rm it before restarting."
  exit 1
fi

# Requested mode: universe (SEARCH_UNIVERSE set) vs list (SEARCH_TICKERS).
REQ_MODE=list
[ -n "${SEARCH_UNIVERSE:-}" ] && REQ_MODE=universe

if tmux has-session -t "$SESSION" 2>/dev/null; then
  CUR_MODE=$(cat "$LOG_DIR/MODE" 2>/dev/null || echo unknown)
  if [ "$CUR_MODE" != "$REQ_MODE" ]; then
    echo "session '$SESSION' is running in '$CUR_MODE' mode but '$REQ_MODE' was requested —"
    echo "run 'make search-off' first (never killed automatically: it may hold hours of work)."
    exit 1
  fi
  echo "session '$SESSION' already running ($CUR_MODE mode) -> tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR/STOP.flag"
echo "$REQ_MODE" > "$LOG_DIR/MODE"

# Bake the mode env into the pane command line rather than relying on tmux's
# environment snapshot (tmux captures the server's env at first-session
# creation, which can be stale/empty for a later relaunch by the supervisor).
MODE_ENV="SEARCH_TICKERS='${SEARCH_TICKERS:-}' SEARCH_UNIVERSE='${SEARCH_UNIVERSE:-}' SEARCH_APPLY_POLICY='${SEARCH_APPLY_POLICY:-}'"
tmux new-session -d -s "$SESSION" -n run "$MODE_ENV bash scripts/_search_run_loop.sh"
tmux set-option -t "$SESSION" remain-on-exit on 2>/dev/null || true
tmux new-window -t "$SESSION" -n watch "bash scripts/_search_watch.sh"

echo "search loop started ($REQ_MODE mode): tmux attach -t $SESSION   (windows: run, watch)"
