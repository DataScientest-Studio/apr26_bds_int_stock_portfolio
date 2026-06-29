# Minimal per-asset pipeline. One operator surface.
#   make deps                 install requirements into ../.venv
#   make build-db             data/seed/*_ohlcv_1h.parquet -> liora.duckdb
#   make run-asset TICKER=AAPL   run the notebook -> Assets/AAPL/ (7 files)
#   make dashboard            refresh Dashboard feed: oos_metrics.db -> Plan/data/dashboard.json
#   make serve                serve the static visualization (Plan/) on :8000 (foreground)
#   make on                   serve Plan/ in the BACKGROUND + open the browser
#   make off                  stop the background viz server (also: make restart / make logs)
#   make clean                remove generated assets + liora.duckdb
PY := ../.venv/bin/python3
PIP := ../.venv/bin/pip
PORT ?= 8000
PID := .viz.pid
LOG := .viz.log

.PHONY: deps build-db run-asset dashboard serve on off restart logs clean help

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

deps:
	$(PIP) install -r requirements.txt

build-db:
	$(PY) build_db.py

run-asset:
	@test -n "$(TICKER)" || (echo "usage: make run-asset TICKER=AAPL" && exit 1)
	$(PY) run_asset.py TICKER=$(TICKER)

dashboard:
	python3 build_dashboard.py

serve:
	$(PY) -m http.server 8000 --directory ../../Plan

clean:
	rm -rf Assets/*/ liora.duckdb oos_metrics.db ../../Plan/data/dashboard.json __pycache__ .ipynb_checkpoints

# --- view the visualization in a browser (background server; static, needs no .venv) ---
on:
	@python3 build_dashboard.py >/dev/null 2>&1 || true
	@if [ -f $(PID) ] && kill -0 $$(cat $(PID)) 2>/dev/null; then echo "  already running (PID $$(cat $(PID)))"; else rm -f $(PID) $(LOG); nohup python3 -m http.server $(PORT) --directory ../../Plan > $(LOG) 2>&1 & echo $$! > $(PID); sleep 1; kill -0 $$(cat $(PID)) 2>/dev/null && echo "  ✅ http://localhost:$(PORT)/index.html (PID $$(cat $(PID)))" || { echo "  ❌ failed to start:"; tail -n 20 $(LOG); rm -f $(PID); exit 1; }; fi
	@xdg-open "http://localhost:$(PORT)/index.html" >/dev/null 2>&1 || true

off:
	@if [ -f $(PID) ]; then kill $$(cat $(PID)) 2>/dev/null && echo "  ✅ stopped"; rm -f $(PID); else echo "  not running"; fi

restart: off on

logs:
	@test -f $(LOG) && tail -f $(LOG) || echo "  no log — try 'make on'"
