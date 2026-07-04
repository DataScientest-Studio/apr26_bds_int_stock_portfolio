#!/usr/bin/env bash
# tmux window "watch": re-arming stall watchdog. ALERT-only — never kills the
# worker (a slow run_asset subprocess is expected and carries its own grace
# period in the heartbeat; a false kill here would lose real work, same
# lesson qc_sp500_1h_jupyters learned the hard way). Loops forever (continuous
# mode); stops only on STOP.flag / HALT.flag. Heartbeat now also carries phase=search +
# in_flight/done/total (parallel rounds); grace_s (1800 search/build_db, 10800 apply) is
# honored as before so a long parallel run_asset batch never false-alarms.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."   # Project/Structure/
LOG_DIR=logs/search
HEARTBEAT="$LOG_DIR/heartbeat.json"
DEFAULT_STALE_S=900

mkdir -p "$LOG_DIR"

while true; do
  [ -f "$LOG_DIR/STOP.flag" ] && { echo "STOP.flag present -> exiting watch loop"; break; }
  [ -f "$LOG_DIR/HALT.flag" ] && { echo "HALT.flag present -> exiting watch loop"; break; }

  if [ -f "$HEARTBEAT" ]; then
    mtime=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
    now=$(date +%s)
    age=$((now - mtime))
    grace=$(python3 -c "import json,sys
try:
    print(int(json.load(open('$HEARTBEAT')).get('grace_s', $DEFAULT_STALE_S)))
except Exception:
    print($DEFAULT_STALE_S)" 2>/dev/null || echo "$DEFAULT_STALE_S")
    threshold=$(( grace > DEFAULT_STALE_S ? grace : DEFAULT_STALE_S ))
    if [ "$age" -gt "$threshold" ]; then
      echo "STALL: heartbeat age ${age}s > threshold ${threshold}s (last: $(cat "$HEARTBEAT"))" \
        | tee -a "$LOG_DIR/ALERTS.txt"
    fi
  fi

  disk_gb=$(df -BG . | awk 'NR==2{gsub("G","",$4); print $4}')
  if [ -n "${disk_gb:-}" ] && [ "$disk_gb" -lt 3 ]; then
    echo "LOW DISK: ${disk_gb}G free" | tee -a "$LOG_DIR/ALERTS.txt"
  fi

  sleep 60
done
