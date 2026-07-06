# 1000-LSTM-Liora. One operator surface.
#   make deps                  create .venv + install pinned requirements (CPU-only torch)
#   make build-data            provenance only: upstream 1h store -> data/sp500_1d.duckdb (data ships committed)
#   make build-cache           precompute CORE+OPTIONAL feature frames -> cache/ (RAM-resident; speeds the loop)
#   make run-asset TICKER=AAPL train the LSTM + one-shot OOS -> Assets/AAPL/ (3 files) + oos_metrics row
#   make loop "AAPL MSFT XOM"  run-asset for each ticker, then refresh the dashboard feed
#   make universe              core-only baseline: EVERY bundled ticker (parallel, resumable)
#   make universe-on / -off    the same, detached in the background (log: .universe.log)
#   make universe-status       done/total progress counter
#   make search / search-on    THE FULL LOOP: parallel per-asset feature selection + OOS per ticker
#                              (self-improving, continuous, resumable; JOBS=<n> to set workers)
#   make search-off / -status  stop the loop / searched-applied counter
#   make search-agent-on       Claude Sonnet /loop proposing new features (tmux; subscription session)
#   make dashboard             oos_metrics.db -> dashboard/data/dashboard.json
#   make stats                 honest one-shot-OOS results snapshot (read-only; for the writeup)
#   make verify                reproduce a diverse sample from the committed manifest == sealed rows
#   make app                   ML Basket Simulator (Streamlit) on :8502 (foreground, Ctrl+C stops)
#   make serve                 serve dashboard/ on :8010 (foreground)
#   make on / make off         background dashboard server on :8010 / stop it
#   make clean                 remove Assets/*/ oos_metrics.db dashboard/data/ __pycache__
PY := .venv/bin/python3
PIP := .venv/bin/pip
ST := .venv/bin/streamlit
APP_PORT ?= 8502
DASH_PORT ?= 8010
PID := .dash.pid
LOG := .dash.log
UPID := .universe.pid
ULOG := .universe.log
SPID := .search.pid
SLOG := logs/search/search.log

LOOP_TICKERS := $(strip $(if $(TICKERS),$(TICKERS),$(filter-out loop,$(MAKECMDGOALS))))
LOOP_TICKERS := $(shell printf '%s' "$(LOOP_TICKERS)" | tr '[:lower:]' '[:upper:]')
ifeq (loop,$(firstword $(MAKECMDGOALS)))
%:
	@:
endif

.PHONY: deps build-data build-cache run-asset loop universe universe-on universe-off universe-status \
        search search-on search-off search-status search-agent-on dashboard stats verify app serve on off clean help

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

deps:
	test -d .venv || python3 -m venv .venv
	$(PIP) install -r requirements.txt

build-data:
	$(PY) tools/build_data.py

build-cache:
	$(PY) tools/build_feature_cache.py

run-asset:
	@test -n "$(TICKER)" || (echo "usage: make run-asset TICKER=AAPL" && exit 1)
	$(PY) run_asset.py TICKER=$(TICKER)

loop:
	@test -n "$(strip $(LOOP_TICKERS))" || (echo "usage: make loop \"AAPL MSFT XOM\"" && exit 1)
	@echo "loop tickers: $(LOOP_TICKERS)"
	@for T in $(LOOP_TICKERS); do echo ">>> run-asset $$T"; $(PY) run_asset.py TICKER=$$T || exit 1; done
	$(PY) build_dashboard.py

universe:
	$(PY) run_universe.py

universe-on:
	@if [ -f $(UPID) ] && kill -0 $$(cat $(UPID)) 2>/dev/null; then \
	  echo "universe loop already running (PID $$(cat $(UPID))) — tail: make universe-status"; \
	else \
	  rm -f $(UPID) $(ULOG); \
	  setsid nohup $(PY) run_universe.py > $(ULOG) 2>&1 & echo $$! > $(UPID); \
	  echo "universe loop started (PID $$(cat $(UPID))), log: $(ULOG)"; \
	fi

universe-off:
	@if [ -f $(UPID) ] && kill -0 $$(cat $(UPID)) 2>/dev/null; then \
	  kill -- -$$(cat $(UPID)) 2>/dev/null || kill $$(cat $(UPID)); \
	  echo "stopped, incl. the in-flight run_asset (resume: make universe-on)"; \
	else echo "not running"; fi; rm -f $(UPID)

universe-status:
	@$(PY) -c "import sqlite3, duckdb; \
	c = duckdb.connect('data/sp500_1d.duckdb', read_only=True); \
	total = c.execute('select count(distinct symbol) from bars_1d').fetchone()[0]; c.close(); \
	import pathlib; db = pathlib.Path('oos_metrics.db'); \
	done = 0 if not db.exists() else sqlite3.connect('file:oos_metrics.db?mode=ro', uri=True).execute('select count(*) from oos_metrics').fetchone()[0]; \
	print(f'{done}/{total} assets done')"
	@tail -n 3 $(ULOG) 2>/dev/null || true

search:
	@mkdir -p logs/search; rm -f logs/search/STOP.flag
	$(PY) feature_search.py

search-on:
	@mkdir -p logs/search; rm -f logs/search/STOP.flag
	@if [ -f $(SPID) ] && kill -0 $$(cat $(SPID)) 2>/dev/null; then \
	  echo "feature-search already running (PID $$(cat $(SPID))) — make search-status"; \
	else \
	  rm -f $(SPID); setsid nohup $(PY) feature_search.py > $(SLOG) 2>&1 & echo $$! > $(SPID); \
	  echo "feature-search started (PID $$(cat $(SPID))), log: $(SLOG)"; \
	fi

search-off:
	@mkdir -p logs/search; touch logs/search/STOP.flag
	@if [ -f $(SPID) ] && kill -0 $$(cat $(SPID)) 2>/dev/null; then \
	  kill -- -$$(cat $(SPID)) 2>/dev/null || kill $$(cat $(SPID)); \
	  echo "stopped, incl. the in-flight run_asset (resume: make search-on)"; \
	else echo "not running"; fi; rm -f $(SPID)

search-status:
	@$(PY) feature_search.py --status
	@tail -n 3 $(SLOG) 2>/dev/null || true

SEARCH_SESSION := lstm_feature_search
search-agent-on:
	@command -v tmux >/dev/null || (echo "tmux not installed" && exit 1)
	@echo '{"halt": false, "proposed_features": []}' > search_control.json 2>/dev/null || true
	@tmux has-session -t $(SEARCH_SESSION) 2>/dev/null || tmux new-session -d -s $(SEARCH_SESSION) -c $(CURDIR)
	tmux send-keys -t $(SEARCH_SESSION) 'claude --model sonnet' Enter
	@sleep 12
	tmux send-keys -t $(SEARCH_SESSION) '/loop 15m /lstm-search-steer' Enter
	@echo "Sonnet feature-proposer started in tmux '$(SEARCH_SESSION)' (a billed claude session)"

dashboard:
	$(PY) build_dashboard.py

stats:
	@$(PY) build_dashboard.py >/dev/null 2>&1 || true
	@$(PY) tools/stats.py

verify:
	@$(PY) tools/verify_repro.py $(TICKERS)

app:
	$(ST) run app.py --server.port $(APP_PORT)

serve:
	@if [ -f $(PID) ] && kill -0 $$(cat $(PID)) 2>/dev/null; then \
	  echo "already served in the background on :$(DASH_PORT) (PID $$(cat $(PID))) -> http://localhost:$(DASH_PORT)/dashboard.html"; \
	  echo "  'make off' to stop it, then 'make serve' for a foreground server."; \
	else \
	  echo "serving dashboard/ at http://localhost:$(DASH_PORT)/dashboard.html  (Ctrl+C to stop)"; \
	  $(PY) -m http.server $(DASH_PORT) --directory dashboard; \
	fi

on:
	@$(PY) build_dashboard.py >/dev/null 2>&1 || true
	@if [ -f $(PID) ] && kill -0 $$(cat $(PID)) 2>/dev/null; then echo "already running: http://localhost:$(DASH_PORT)/dashboard.html (PID $$(cat $(PID)))"; else rm -f $(PID) $(LOG); nohup $(PY) -m http.server $(DASH_PORT) --directory dashboard > $(LOG) 2>&1 & echo $$! > $(PID); sleep 1; kill -0 $$(cat $(PID)) 2>/dev/null && echo "http://localhost:$(DASH_PORT)/dashboard.html (PID $$(cat $(PID)))" || { echo "failed to start:"; tail -n 20 $(LOG); rm -f $(PID); exit 1; }; fi

off:
	@if [ -f $(PID) ]; then kill $$(cat $(PID)) 2>/dev/null && echo "stopped"; rm -f $(PID); else echo "not running"; fi

clean:
	rm -rf Assets/*/ oos_metrics.db dashboard/data __pycache__
