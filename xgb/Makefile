# liora-project-ml-engineering — presentation build. One operator surface.
#   make deps                    create .venv + install pinned requirements
#   make app                     ML Basket Simulator (Streamlit) on :8501 — shows the sealed results
#   make on / make off           background Plan site on :8000 (index + dashboard) / stop it
#   make dashboard               refresh the OOS feed: data/oos_metrics.db -> plan/data/dashboard.json
#   make verify                  reproduce the demo tickers from the bundled mini-bars == sealed rows
#   make run-asset TICKER=AAPL   run the notebook pipeline -> Assets/AAPL/ (7 files) + a results row
#   make feature-search          print the active feature manifest (read-only)
#   make build-db                FULL universe: external upstream store -> data/liora.duckdb (needs SP500_DUCKDB)
#   make loop "AAPL TSLA XOM"    run each ticker, then refresh the dashboard feed
#   make serve                   serve plan/ on :8000 (foreground)
#   make clean                   remove run scratch (Assets/*/ __pycache__) — keeps the sealed data/
PY := .venv/bin/python3
PIP := .venv/bin/pip
ST := .venv/bin/streamlit
PORT ?= 8000
APP_PORT ?= 8501
PID := .viz.pid
LOG := .viz.log
# Full-universe bars come from an external upstream store (single-homed in src/bars.py; override here).
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

.PHONY: deps app on off restart logs dashboard verify run-asset feature-search build-db loop serve clean help

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

deps:
	test -d .venv || python3 -m venv .venv
	$(PIP) install -r requirements.txt

app:
	$(ST) run app/app.py --server.port $(APP_PORT)

dashboard:
	$(PY) src/build_dashboard.py

verify:
	@$(PY) tools/verify_repro.py $(TICKERS)

run-asset:
	@test -n "$(TICKER)" || (echo "usage: make run-asset TICKER=AAPL" && exit 1)
	$(PY) src/run_asset.py TICKER=$(TICKER)

define FEATURE_MANIFEST_PY
import sys
sys.path.insert(0, "src")
import pipeline as P
m = P.resolve_feature_manifest(None)
print("Active feature manifest")
print("schema:", m["schema_version"])
print("namespaces:", ", ".join(m["active_namespaces"]))
for block in m["per_namespace"]:
    print("%s %s: %d features" % (block["namespace"], block["id_range"], block["feature_count"]))
endef
export FEATURE_MANIFEST_PY

feature-search:
	@$(PY) -c "$$FEATURE_MANIFEST_PY"

build-db:
	SP500_DUCKDB="$(SP500_DUCKDB)" $(PY) src/build_db.py

loop:
	@echo "loop tickers: $(LOOP_TICKERS)"
	@for T in $(LOOP_TICKERS); do echo ">>> run-asset $$T"; $(PY) src/run_asset.py TICKER=$$T || exit 1; done
	$(PY) src/build_dashboard.py

serve:
	@if [ -f $(PID) ] && kill -0 $$(cat $(PID)) 2>/dev/null; then \
	  echo "already served in the background on :$(PORT) (PID $$(cat $(PID))) -> http://localhost:$(PORT)/index.html"; \
	  echo "  'make off' to stop it, then 'make serve' to run in the foreground."; \
	elif ss -ltn 2>/dev/null | grep -q ':$(PORT) '; then \
	  echo "port $(PORT) already in use -> open http://localhost:$(PORT)/index.html"; \
	else \
	  echo "serving plan/ at http://localhost:$(PORT)/index.html  (Ctrl+C to stop)"; \
	  $(PY) -m http.server $(PORT) --directory plan; \
	fi

on:
	@$(PY) src/build_dashboard.py >/dev/null 2>&1 || true
	@if [ -f $(PID) ] && kill -0 $$(cat $(PID)) 2>/dev/null; then echo "already running: http://localhost:$(PORT)/index.html (PID $$(cat $(PID)))"; else rm -f $(PID) $(LOG); nohup $(PY) -m http.server $(PORT) --directory plan > $(LOG) 2>&1 & echo $$! > $(PID); sleep 1; kill -0 $$(cat $(PID)) 2>/dev/null && echo "http://localhost:$(PORT)/index.html (PID $$(cat $(PID)))" || { echo "failed to start:"; tail -n 20 $(LOG); rm -f $(PID); exit 1; }; fi
	@xdg-open "http://localhost:$(PORT)/index.html" >/dev/null 2>&1 || true

off:
	@if [ -f $(PID) ]; then kill $$(cat $(PID)) 2>/dev/null && echo "stopped"; rm -f $(PID); else echo "not running"; fi

restart: off on

logs:
	@test -f $(LOG) && tail -f $(LOG) || echo "no log; try 'make on'"

clean:
	rm -rf Assets/*/ __pycache__ src/__pycache__ app/__pycache__ tools/__pycache__ .ipynb_checkpoints
