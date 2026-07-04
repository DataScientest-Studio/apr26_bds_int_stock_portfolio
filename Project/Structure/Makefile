# Minimal per-asset pipeline. One operator surface.
#   make deps                    install requirements into ../.venv
#   make build-db                data/seed/*_ohlcv_1h.parquet -> liora.duckdb
#   make run-asset TICKER=AAPL   run the notebook -> Assets/AAPL/ (7 files)
#   make feature-search          print the active simple feature manifest
#   make loop "AAPL TSLA XOM"    ensure seeds -> build-db -> run each ticker -> dashboard
#   make dashboard               refresh Dashboard feed: oos_metrics.db -> Plan/data/dashboard.json
#   make build                   regenerate Plan/*.html from *.tmpl + Markdown markers (single-home-per-fact)
#   make check                   fail-closed gate: number drift / stray literals / lego<->SOT crossmatch
#   make ensure-seeds            export any missing SEARCH_TICKERS seeds from SP500_DUCKDB
#   make search-on               launch the continuous per-asset feature-search loop (S.1, tmux, supervised)
#   make search-off              stop the search loop gracefully (STOP.flag) and its supervisor
#   make search-status           one-shot per-ticker search status (sqlite, read-only)
#   make search-logs             tail the search worker log
#   make search-apply TICKER=X   manual re-apply of the current Train-CV best (a SECOND OOS read)
#   make search-agent-on         start the Claude Sonnet steering session (/feature-search-steer)
#   make serve                   serve the static visualization (Plan/) on :8000 (foreground)
#   make on                      serve Plan/ in the background + open the browser
#   make off                     stop the background viz server
#   make restart                 restart the background viz server (off + on)
#   make logs                    tail the background viz server log
#   make clean                   remove generated assets + liora.duckdb
PY := ../.venv/bin/python3
PIP := ../.venv/bin/pip
PORT ?= 8000
PID := .viz.pid
LOG := .viz.log
SP500_DUCKDB := /opt/to_liora_school/qc-raw-ohlcv-data-sp500-alpaca/endproduct/ohlcv_1h_sp500_alpaca.duckdb

LOOP_TICKERS := $(strip $(if $(TICKERS),$(TICKERS),$(filter-out loop,$(MAKECMDGOALS))))
ifeq ($(strip $(LOOP_TICKERS)),)
LOOP_TICKERS := AAPL TSLA XOM
endif
LOOP_TICKERS := $(shell printf '%s' "$(LOOP_TICKERS)" | tr '[:lower:]' '[:upper:]')
ifeq (loop,$(firstword $(MAKECMDGOALS)))
%:
	@:
endif

SEARCH_TICKERS ?= AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO LLY JPM V UNH XOM MA COST PG HD JNJ WMT NFLX
SEARCH_SESSION := liora_feature_search
SEARCH_LOG_DIR := logs/search
SEARCH_SUP_PID := .search_supervisor.pid

.PHONY: deps build-db run-asset feature-search loop dashboard build check serve on off restart logs clean help \
        ensure-seeds search-on search-off search-status search-logs search-apply search-agent-on

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

build:
	python3 config/data_state_numbers_gate.py build

check:
	python3 config/data_state_numbers_gate.py check

deps:
	$(PIP) install -r requirements.txt

build-db:
	$(PY) build_db.py

run-asset:
	@test -n "$(TICKER)" || (echo "usage: make run-asset TICKER=AAPL" && exit 1)
	$(PY) run_asset.py TICKER=$(TICKER)

define FEATURE_MANIFEST_PY
import sys
sys.path.insert(0, ".")
import pipeline as P
m = P.resolve_feature_manifest(None)
print("Active feature manifest")
print("schema:", m["schema_version"])
print("namespaces:", ", ".join(m["active_namespaces"]))
for block in m["per_namespace"]:
    print("%s %s: %d features" % (block["namespace"], block["id_range"], block["feature_count"]))
    for fid, name in zip(block["feature_ids"], block["feature_names"]):
        print("  %3d  %s" % (fid, name))
endef
export FEATURE_MANIFEST_PY

feature-search:
	@$(PY) -c "$$FEATURE_MANIFEST_PY"

define ENSURE_SEEDS_PY
import os
from pathlib import Path
import pandas as pd
TICKERS = os.environ.get("LOOP_TICKERS", "AAPL TSLA XOM").split()
SP500_DUCKDB = os.environ.get("SP500_DUCKDB", "")
seed_dir = Path("data/seed")
seed_dir.mkdir(parents=True, exist_ok=True)
missing = [T for T in TICKERS if not (seed_dir / ("%s_ohlcv_1h.parquet" % T)).exists()]
if missing:
    if not SP500_DUCKDB or not Path(SP500_DUCKDB).exists():
        raise SystemExit("missing seed(s) %s and SP500_DUCKDB unavailable (%s)" % (", ".join(missing), SP500_DUCKDB))
    import duckdb
    con = duckdb.connect(SP500_DUCKDB, read_only=True)
    for T in missing:
        out = seed_dir / ("%s_ohlcv_1h.parquet" % T)
        d = con.execute("select ts as timestamp, open, high, low, close, volume from ohlcv_1h where symbol=? order by ts", [T]).fetchdf()
        if d.empty:
            raise SystemExit("ticker %s not found in %s" % (T, SP500_DUCKDB))
        d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.tz_localize("America/New_York", ambiguous="infer", nonexistent="shift_forward").dt.tz_convert("UTC")
        d["volume"] = d["volume"].astype("float64")
        d = d[["timestamp", "open", "high", "low", "close", "volume"]]
        d.to_parquet(out, index=False)
        print("exported seed %s (%d bars)" % (out, len(d)))
    con.close()
else:
    print("all requested seeds already present")
endef
export ENSURE_SEEDS_PY

loop:
	@echo "loop tickers: $(LOOP_TICKERS)"
	@LOOP_TICKERS="$(LOOP_TICKERS)" SP500_DUCKDB="$(SP500_DUCKDB)" $(PY) -c "$$ENSURE_SEEDS_PY"
	$(PY) build_db.py
	@for T in $(LOOP_TICKERS); do echo ">>> run-asset $$T"; $(PY) run_asset.py TICKER=$$T || exit 1; done
	python3 build_dashboard.py

dashboard:
	python3 build_dashboard.py

ensure-seeds:
	@LOOP_TICKERS="$(SEARCH_TICKERS)" SP500_DUCKDB="$(SP500_DUCKDB)" $(PY) -c "$$ENSURE_SEEDS_PY"

search-on: ensure-seeds
	@SEARCH_TICKERS="$(SEARCH_TICKERS)" bash scripts/search_on.sh
	@if [ -f $(SEARCH_SUP_PID) ] && kill -0 $$(cat $(SEARCH_SUP_PID)) 2>/dev/null; then \
	  echo "supervisor already running (PID $$(cat $(SEARCH_SUP_PID)))"; \
	else \
	  mkdir -p $(SEARCH_LOG_DIR); \
	  SEARCH_TICKERS="$(SEARCH_TICKERS)" nohup bash scripts/_search_supervisor.sh >> $(SEARCH_LOG_DIR)/supervisor.log 2>&1 & \
	  echo $$! > $(SEARCH_SUP_PID); \
	  echo "supervisor started (PID $$(cat $(SEARCH_SUP_PID)))"; \
	fi
	@echo "monitor: tmux attach -t $(SEARCH_SESSION)   (windows: run, watch)"
	@echo "or:      make search-status / make search-logs"

search-off:
	@mkdir -p $(SEARCH_LOG_DIR)
	@touch $(SEARCH_LOG_DIR)/STOP.flag
	@echo "STOP.flag set; waiting up to 20s for the loop to exit gracefully..."
	@for i in $$(seq 1 20); do tmux has-session -t $(SEARCH_SESSION) 2>/dev/null || break; sleep 1; done
	@tmux kill-session -t $(SEARCH_SESSION) 2>/dev/null || true
	@if [ -f $(SEARCH_SUP_PID) ]; then kill $$(cat $(SEARCH_SUP_PID)) 2>/dev/null || true; rm -f $(SEARCH_SUP_PID); fi
	@echo "search loop stopped"

search-status:
	@$(PY) feature_search_worker.py --status

search-logs:
	@test -f $(SEARCH_LOG_DIR)/worker.log && tail -f $(SEARCH_LOG_DIR)/worker.log || echo "no log; try 'make search-on'"

search-apply:
	@test -n "$(TICKER)" || (echo "usage: make search-apply TICKER=AAPL" && exit 1)
	$(PY) feature_search_worker.py --apply $(TICKER)

search-agent-on:
	@tmux has-session -t $(SEARCH_SESSION) 2>/dev/null || (echo "run 'make search-on' first" && exit 1)
	@tmux list-windows -t $(SEARCH_SESSION) -F '#W' | grep -qx agent || \
	  tmux new-window -t $(SEARCH_SESSION) -n agent -c $(CURDIR)/../..
	tmux send-keys -t $(SEARCH_SESSION):agent 'claude --model sonnet' Enter
	@sleep 15
	tmux send-keys -t $(SEARCH_SESSION):agent '/loop 15m /feature-search-steer' Enter
	@echo "agent steering started in tmux window '$(SEARCH_SESSION):agent'"

serve:
	$(PY) -m http.server 8000 --directory ../../Plan

clean:
	rm -rf Assets/*/ liora.duckdb oos_metrics.db ../../Plan/data/dashboard.json __pycache__ .ipynb_checkpoints

on:
	@python3 build_dashboard.py >/dev/null 2>&1 || true
	@if [ -f $(PID) ] && kill -0 $$(cat $(PID)) 2>/dev/null; then echo "already running (PID $$(cat $(PID)))"; else rm -f $(PID) $(LOG); nohup python3 -m http.server $(PORT) --directory ../../Plan > $(LOG) 2>&1 & echo $$! > $(PID); sleep 1; kill -0 $$(cat $(PID)) 2>/dev/null && echo "http://localhost:$(PORT)/index.html (PID $$(cat $(PID)))" || { echo "failed to start:"; tail -n 20 $(LOG); rm -f $(PID); exit 1; }; fi
	@xdg-open "http://localhost:$(PORT)/index.html" >/dev/null 2>&1 || true

off:
	@if [ -f $(PID) ]; then kill $$(cat $(PID)) 2>/dev/null && echo "stopped"; rm -f $(PID); else echo "not running"; fi

restart: off on

logs:
	@test -f $(LOG) && tail -f $(LOG) || echo "no log; try 'make on'"
