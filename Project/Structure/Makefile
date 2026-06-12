# =============================================================================
# Liora ML Engineering — minimal pipeline
#   Bash + DuckDB + SQL + XGBoost/Optuna + Streamlit
#
# One database (liora.duckdb), one production model (XGBoost+Optuna), one
# requirements.txt. Data & model artifacts live in the active run
# (Archive/runs/<ACTIVE_RUN>) and are reached via Project/endproduct/ symlinks.
#
# Quick start (from Project/Structure):
#   make setup          # ../.venv + install requirements.txt
#   make build-db       # build liora.duckdb from the run's frozen CSVs
#   make pipeline       # train (Optuna) → walk-forward → portfolios
#   make app            # Streamlit defense demo
# =============================================================================

SHELL          := /bin/bash
.SHELLFLAGS    := -eu -o pipefail -c
.DEFAULT_GOAL  := help

VENV           ?= ../.venv
PYTHON         ?= $(VENV)/bin/python
PIP            ?= $(VENV)/bin/pip
STREAMLIT      ?= $(VENV)/bin/streamlit

ENDPRODUCT_DIR := ../endproduct
ACTIVE_RUN     := 2026-06-08          # mirrors config/paths.yaml
DATA_DIR       := $(ENDPRODUCT_DIR)/data
MODELS_DIR     := $(ENDPRODUCT_DIR)/models
RENDERING1_DIR := ../../Formalities/Rendering1

FETCH_ARGS     ?=
TRIALS         ?= 30
APP_PORT       ?= 8501
PID_FILE       := .streamlit.pid
LOG_FILE       := .streamlit.log

define banner
	@printf "\n\033[1;36m▶ %s\033[0m\n" "$(1)"
endef

# =============================================================================
##@ SETUP
# =============================================================================
.PHONY: help setup venv freeze

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "; \
		printf "\n\033[1mLiora — minimal pipeline\033[0m\nUsage: make \033[36m<target>\033[0m\n"} \
		/^##@ / {printf "\n\033[1;33m%s\033[0m\n", substr($$0, 5); next} \
		/^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)
	@echo ""

$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV)/bin/python ## Create ../.venv

setup: $(VENV)/bin/python ## Create ../.venv and install requirements.txt
	$(call banner,Installing requirements.txt)
	$(PIP) install -r requirements.txt
	@echo "✅ Environment ready. Next: make build-db && make app"

freeze: ## Snapshot the venv to requirements.lock.txt
	$(PIP) freeze > requirements.lock.txt

# =============================================================================
##@ DATA — DuckDB is the single store
# =============================================================================
.PHONY: fetch fetch-smoke build-db audit

fetch: ## Download S&P 500 OHLCV from Alpaca → liora.duckdb (new runs)
	$(call banner,Fetching S&P 500 from Alpaca → DuckDB)
	$(PYTHON) fetch_data.py $(FETCH_ARGS)

fetch-smoke: ## Fetch 20 tickers only (smoke test)
	$(PYTHON) fetch_data.py --limit 20

build-db: ## Build liora.duckdb from the active run's frozen CSV artifacts
	$(call banner,Building liora.duckdb from frozen CSVs)
	$(PYTHON) ingest_to_duckdb.py

audit: ## Print data-quality KPIs (SQL) from liora.duckdb
	$(call banner,Data audit)
	@$(PYTHON) run_sql.py audit.sql --print --read-only

# =============================================================================
##@ MODEL — one production pipeline (XGBoost + Optuna)
# =============================================================================
.PHONY: train walk-forward portfolios pipeline

train: ## Tune (Optuna) + train the production XGBoost model → DuckDB
	$(call banner,Training XGBoost + Optuna [$(TRIALS) trials])
	$(PYTHON) train_xgb_optuna.py --trials $(TRIALS)

walk-forward: ## Expanding-window walk-forward backtest → DuckDB
	$(call banner,Walk-forward backtest)
	./walk_forward.sh

portfolios: ## Build 3 sector-capped portfolios from model rankings (SQL)
	$(call banner,Building portfolios [SQL])
	$(PYTHON) run_sql.py build_portfolios.sql
	@echo "✅ portfolio_* tables written."

pipeline: train walk-forward portfolios ## train → walk-forward → portfolios
	@echo "✅ Pipeline complete. Run 'make app'."

# =============================================================================
##@ APP — Streamlit defense demo
# =============================================================================
.PHONY: app on off restart logs

app: ## Run Streamlit in the foreground (Ctrl+C stops)
	$(call banner,Launching Streamlit on :$(APP_PORT))
	$(STREAMLIT) run app.py --server.port $(APP_PORT)

on: ## Start Streamlit in the background
	$(call banner,Starting Streamlit on :$(APP_PORT))
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "  Already running (PID $$(cat $(PID_FILE)))"; \
	else \
		rm -f $(PID_FILE) $(LOG_FILE); \
		nohup $(STREAMLIT) run app.py --server.port $(APP_PORT) --server.headless true \
			> $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE); \
		sleep 2; \
		kill -0 $$(cat $(PID_FILE)) 2>/dev/null \
			&& echo "  ✅ http://localhost:$(APP_PORT) (PID $$(cat $(PID_FILE)))" \
			|| { echo "  ❌ failed:"; tail -n 20 $(LOG_FILE); rm -f $(PID_FILE); exit 1; }; \
	fi

off: ## Stop the background Streamlit
	@if [ -f $(PID_FILE) ]; then kill $$(cat $(PID_FILE)) 2>/dev/null && echo "  ✅ stopped"; rm -f $(PID_FILE); \
	else echo "  not running"; fi

restart: off on ## Restart the background app

logs: ## Tail the background app log
	@test -f $(LOG_FILE) && tail -f $(LOG_FILE) || echo "  no log — try 'make on'"

# =============================================================================
##@ REPORT — Rendering 1 PDF (matplotlib figures, offline)
# =============================================================================
.PHONY: figures report-pdf report

figures: ## Regenerate the 6 EDA figures (PNG) for the PDF
	$(PYTHON) reports/make_figures.py

report-pdf: ## Build the Rendering 1 PDF (pandoc + xelatex)
	reports/build_pdf.sh

report: figures report-pdf ## Figures + PDF

# =============================================================================
##@ QUALITY
# =============================================================================
.PHONY: test syntax-check status clean

test: ## Parity (features) + headless app smoke test
	$(call banner,Feature parity)
	$(PYTHON) tests/parity_features.py
	$(call banner,App smoke)
	$(PYTHON) tests/smoke_app.py

syntax-check: ## Byte-compile all sources
	$(PYTHON) -m compileall -q app.py fetch_data.py train_xgb_optuna.py ingest_to_duckdb.py run_sql.py src tests

status: ## Show what's present
	@echo "📦 venv:    $$(test -x $(PYTHON) && $(PYTHON) --version || echo missing)"
	@echo "🦆 duckdb:  $$(test -f $(DATA_DIR)/liora.duckdb && echo "✅ $$(du -hL $(DATA_DIR)/liora.duckdb | cut -f1)" || echo "❌ run make build-db")"
	@echo "🤖 model:   $$(test -f $(MODELS_DIR)/xgb_model.json && echo "✅ xgb_model.json" || echo "❌ run make train")"
	@echo "📄 report:  $$(ls $(RENDERING1_DIR)/*.pdf 2>/dev/null | head -1 || echo "(none)")"

clean: ## Remove caches + app PID/log
	$(call banner,Cleaning caches)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f $(PID_FILE) $(LOG_FILE)
	@echo "✅ cleaned (data/models/.venv kept)."
