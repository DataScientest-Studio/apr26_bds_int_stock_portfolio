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
#   make feature-search-loop     PRIMARY loop: full-universe parallel search (503 tickers, SEARCH_JOBS workers, triage -> deepen, apply-at-convergence)
#   make search-on SEARCH_TICKERS="AAPL XOM"   legacy sequential list mode for testing (requires an explicit list, apply-on-satisfied)
#   make search-install-cron     install @reboot + */15 cron so the loop always runs on the server (survives reboot)
#   make search-uninstall-cron   remove the cron entries
#   make search-off              stop the search loop gracefully (STOP.flag) and its supervisor
#   make search-status           one-shot per-ticker search status (sqlite, read-only)
#   make search-logs             tail the search worker log
#   make search-apply TICKER=X   manual re-apply of the current Train-CV best (a SECOND OOS read)
#   make search-agent-on         start the Claude Sonnet steering session (/feature-search-steer)
#   make serve                   serve the static visualization (Plan/) on :8000 (foreground)
#   make app                     ML Basket Simulator demo (Streamlit) on :8501 (foreground, Ctrl+C stops)
#   make on                      serve Plan/ in the background + open the browser
#   make off                     stop the background viz server
#   make restart                 restart the background viz server (off + on)
#   make logs                    tail the background viz server log
#   make clean                   remove generated assets + liora.duckdb
PY := ../.venv/bin/python3
PIP := ../.venv/bin/pip
ST := ../.venv/bin/streamlit
PORT ?= 8000
APP_PORT ?= 8501
PID := .viz.pid
LOG := .viz.log
# Upstream store path lives in seeds.py (single home); set SP500_DUCKDB only to override it.
SP500_DUCKDB ?=

LOOP_TICKERS := $(strip $(if $(TICKERS),$(TICKERS),$(filter-out loop,$(MAKECMDGOALS))))
ifeq ($(strip $(LOOP_TICKERS)),)
LOOP_TICKERS := AAPL TSLA XOM
endif
LOOP_TICKERS := $(shell printf '%s' "$(LOOP_TICKERS)" | tr '[:lower:]' '[:upper:]')
ifeq (loop,$(firstword $(MAKECMDGOALS)))
%:
	@:
endif

# SEARCH_TICKERS: no default — list mode (make search-on) is an explicit-list testing primitive.
SEARCH_TICKERS ?=
SEARCH_UNIVERSE ?= all
SEARCH_JOBS ?=              # parallel search workers (empty -> worker uses cpu_count-1; e.g. 3 on 4 cores)
APPLY_JOBS ?=              # parallel run_asset in the apply phase (empty -> = SEARCH_JOBS)
SEARCH_SESSION := liora_feature_search
SEARCH_LOG_DIR := logs/search
SEARCH_SUP_PID := .search_supervisor.pid

.PHONY: deps build-db run-asset feature-search loop dashboard build check serve app on off restart logs clean help \
        ensure-seeds search-on feature-search-loop search-off search-status search-logs search-apply search-agent-on \
        search-install-cron search-uninstall-cron

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

loop:
	@echo "loop tickers: $(LOOP_TICKERS)"
	@LOOP_TICKERS="$(LOOP_TICKERS)" SP500_DUCKDB="$(SP500_DUCKDB)" $(PY) seeds.py
	$(PY) build_db.py
	@for T in $(LOOP_TICKERS); do echo ">>> run-asset $$T"; $(PY) run_asset.py TICKER=$$T || exit 1; done
	python3 build_dashboard.py

dashboard:
	python3 build_dashboard.py

ensure-seeds:
	@LOOP_TICKERS="$(SEARCH_TICKERS)" SP500_DUCKDB="$(SP500_DUCKDB)" $(PY) seeds.py

# Shared launcher tail: start the outer supervisor once (PID file), print monitor hints.
# $(SEARCH_ENV) carries the mode env into both search_on.sh and the supervisor's relaunches.
define SEARCH_SUP_START
	@if [ -f $(SEARCH_SUP_PID) ] && kill -0 $$(cat $(SEARCH_SUP_PID)) 2>/dev/null; then \
	  echo "supervisor already running (PID $$(cat $(SEARCH_SUP_PID)))"; \
	else \
	  mkdir -p $(SEARCH_LOG_DIR); \
	  $(SEARCH_ENV) nohup bash scripts/_search_supervisor.sh >> $(SEARCH_LOG_DIR)/supervisor.log 2>&1 & \
	  echo $$! > $(SEARCH_SUP_PID); \
	  echo "supervisor started (PID $$(cat $(SEARCH_SUP_PID)))"; \
	fi
	@echo "monitor: tmux attach -t $(SEARCH_SESSION)   (windows: run, watch)"
	@echo "or:      make search-status / make search-logs"
endef

search-on: SEARCH_ENV = SEARCH_TICKERS="$(SEARCH_TICKERS)"
search-on: ensure-seeds
	@test -n "$(SEARCH_TICKERS)" || (echo "usage: make search-on SEARCH_TICKERS=\"AAPL XOM\"  (no default; for the full run use make feature-search-loop)" && exit 1)
	@$(SEARCH_ENV) bash scripts/search_on.sh
	$(SEARCH_SUP_START)

feature-search-loop: SEARCH_ENV = SEARCH_UNIVERSE="$(SEARCH_UNIVERSE)" SEARCH_JOBS="$(SEARCH_JOBS)" APPLY_JOBS="$(APPLY_JOBS)"
feature-search-loop:
	@$(SEARCH_ENV) bash scripts/search_on.sh
	$(SEARCH_SUP_START)

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

CRON_MARK := liora-feature-search-loop
search-install-cron:
	@CMD="bash -lc 'cd $(CURDIR) && bash scripts/search_cron.sh >> logs/search/cron.log 2>&1'"; \
	( crontab -l 2>/dev/null | grep -v "$(CRON_MARK)"; \
	  echo "@reboot $$CMD # $(CRON_MARK)"; \
	  echo "*/15 * * * * $$CMD # $(CRON_MARK)" ) | crontab -
	@echo "installed cron (@reboot + */15) for the full-universe loop:"; crontab -l | grep "$(CRON_MARK)"

search-uninstall-cron:
	@crontab -l 2>/dev/null | grep -v "$(CRON_MARK)" | crontab - || true
	@echo "removed cron entries tagged $(CRON_MARK)"

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

app:
	$(ST) run app.py --server.port $(APP_PORT)

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
