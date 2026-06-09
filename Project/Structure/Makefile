# =============================================================================
# Stocks Recommender Based on User Profile — Liora ML Engineering project
#
# Live code root (Project/Structure). Data & models live in the active run
# (Archive/runs/<ACTIVE_RUN>) and are reached via Project/endproduct/ symlinks.
#
# Quick start (from Project/Structure):
#   make            # show this help
#   make setup      # create ../.venv and install all deps
#   make app        # run the Streamlit defense demo
#   make pipeline   # retrain best model → walk-forward → portfolios (reuses run data)
# =============================================================================

# --- config -----------------------------------------------------------------
SHELL          := /bin/bash
.SHELLFLAGS    := -eu -o pipefail -c
.DEFAULT_GOAL  := help

VENV           ?= ../.venv
PYTHON         ?= ./$(VENV)/bin/python
PIP            ?= ./$(VENV)/bin/pip
STREAMLIT      ?= ./$(VENV)/bin/streamlit

# 3-pillar layout (relative to Project/Structure)
ENDPRODUCT_DIR := ../endproduct
ARCHIVE_DIR    := ../../Archive
ACTIVE_RUN     := 2026-06-08
RENDERING1_DIR := ../../Formalities/Rendering1

ROOT_REQ       := requirements.txt
MODEL_REQ      := $(ARCHIVE_DIR)/runs/$(ACTIVE_RUN)/requirements.txt
DATA_DIR       := $(ENDPRODUCT_DIR)/data
MODELS_DIR     := $(ENDPRODUCT_DIR)/models
REPORTS_DIR    := reports

# Modeling flags (override on CLI, e.g. `make fetch FETCH_ARGS="--limit 20"`)
FETCH_ARGS     ?=
APP_PORT       ?= 8501

# Background-app bookkeeping (used by `make on` / `make off`)
PID_FILE       := .streamlit.pid
LOG_FILE       := .streamlit.log

# Pretty banner for grouped output
define banner
	@printf "\n\033[1;36m▶ %s\033[0m\n" "$(1)"
endef

# =============================================================================
##@ SETUP — environment & dependencies
# =============================================================================

.PHONY: help setup venv install install-mac install-all freeze

help: ## Show this help (auto-generated from doc comments)
	@awk 'BEGIN {FS = ":.*?## "; \
		printf "\n\033[1mStocks Recommender — Makefile\033[0m\n"; \
		printf "Usage: make \033[36m<target>\033[0m\n"} \
		/^##@ / {printf "\n\033[1;33m%s\033[0m\n", substr($$0, 5); next} \
		/^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)
	@echo ""

$(VENV)/bin/python: ## (internal) create the virtualenv at ../.venv
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV)/bin/python ## Create ../.venv (no deps installed)

install: $(VENV)/bin/python ## Install root requirements (app + EDA)
	$(call banner,Installing root requirements)
	$(PIP) install -r $(ROOT_REQ)

install-mac: $(VENV)/bin/python ## Install modeling extras (sklearn, xgboost, ROCm torch) from the active run
	$(call banner,Installing modeling requirements ($(MODEL_REQ)))
	$(PIP) install -r $(MODEL_REQ)

install-all: install install-mac ## Install root + modeling requirements

setup: install-all ## Full setup: ../.venv + all dependencies
	@echo "✅ Environment ready. Next: make app (or make pipeline to retrain)."

freeze: ## Snapshot the active venv into requirements.lock.txt
	$(PIP) freeze > requirements.lock.txt
	@echo "✅ Wrote requirements.lock.txt"

# =============================================================================
##@ STEP 1 — Data mining (acquisition from Alpaca)
# =============================================================================

.PHONY: fetch fetch-smoke data-check

fetch: ## Download S&P 500 OHLCV via Alpaca into the active run (endproduct/data)
	$(call banner,Fetching S&P 500 from Alpaca [writes to active run])
	$(PYTHON) fetch_data.py $(FETCH_ARGS)

fetch-smoke: ## Quick smoke test: fetch 20 tickers only
	$(call banner,Fetching S&P 500 from Alpaca [smoke: 20 tickers])
	$(PYTHON) fetch_data.py --limit 20

data-check: ## Print row counts / date ranges from the active run
	$(call banner,Data inventory)
	@ls -lh $(DATA_DIR)/*.csv 2>/dev/null || echo "  (no data files — check endproduct/data symlink)"
	@$(PYTHON) -c "import pandas as pd, pathlib; \
p=pathlib.Path('$(DATA_DIR)/prices_long.csv'); \
print('prices_long.csv: missing') if not p.exists() else \
(lambda d: print(f'  rows={len(d):,}  tickers={d.ticker.nunique()}  date={d.date.min()}→{d.date.max()}'))(pd.read_csv(p, parse_dates=['date']))" 2>/dev/null || true

# =============================================================================
##@ STEP 2 — Pre-processing & figures → Rendering 1 (PDF)
# =============================================================================

.PHONY: figures report-pdf report

figures: ## Regenerate EDA figures (written to Formalities/Rendering1/figures via symlink)
	$(call banner,Building report figures)
	$(PYTHON) $(REPORTS_DIR)/make_figures.py

report-pdf: ## Build Formalities/Rendering1 PDF via pandoc + xelatex
	$(call banner,Building Rendering 1 PDF)
	$(REPORTS_DIR)/build_pdf.sh

report: figures report-pdf ## Figures + PDF in one shot

# =============================================================================
##@ STEP 3 — Modeling (stages 1–6 + builder). Writes to the active run.
# =============================================================================

.PHONY: train-baseline train-rf train-rf-no-history train-xgboost train-rocm \
        train-all walk-forward

train-baseline: ## Stage 1 — Ridge linear baseline
	$(call banner,Training Ridge baseline [Stage 1])
	$(PYTHON) models/train_first_model.py

train-rf: ## Stage 2 — Random Forest
	$(call banner,Training Random Forest [Stage 2])
	$(PYTHON) models/train_random_forest_model.py

train-rf-no-history: ## Stage 4 — RF without history_days (current best)
	$(call banner,Training Random Forest no-history [Stage 4 — BEST])
	$(PYTHON) models/train_random_forest_no_history_model.py

train-xgboost: ## Stage 5 — XGBoost comparison
	$(call banner,Training XGBoost no-history [Stage 5])
	$(PYTHON) models/train_xgboost_no_history_model.py

train-rocm: ## Stage 3.3 — ROCm PyTorch (AMD GPU deep learning)
	$(call banner,Training ROCm PyTorch model [Stage 3.3 — DL])
	HSA_ENABLE_DXG_DETECTION=1 $(PYTHON) models/train_rocm_model.py

train-all: train-baseline train-rf train-rf-no-history train-xgboost train-rocm ## All 5 models, in order

walk-forward: ## Stage 6 — walk-forward backtest on RF no-history
	$(call banner,Walk-forward backtest [Stage 6])
	$(PYTHON) models/walk_forward_random_forest_no_history.py

# =============================================================================
##@ STEP 3.x — Portfolio construction
# =============================================================================

.PHONY: portfolios

portfolios: ## Stage 7 — build conservative / balanced / aggressive portfolios
	$(call banner,Building portfolios [Stage 7])
	$(PYTHON) models/build_portfolios.py
	@echo ""
	@echo "📊 Portfolio outputs:"
	@ls -lh $(MODELS_DIR)/portfolio_*.csv 2>/dev/null || true

# =============================================================================
##@ STEP 5 — Streamlit defense demo (on / off / restart / logs)
# =============================================================================

.PHONY: on off restart logs app

on: ## Turn the app ON — start Streamlit in background (URL printed at the end)
	$(call banner,Starting Streamlit on :$(APP_PORT))
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "  Already running (PID $$(cat $(PID_FILE))) on http://localhost:$(APP_PORT)"; \
		echo "  Use 'make off' to stop, or 'make restart' to reload."; \
	else \
		rm -f $(PID_FILE) $(LOG_FILE); \
		nohup $(STREAMLIT) run app.py --server.port $(APP_PORT) --server.headless true \
			> $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE); \
		sleep 2; \
		if kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
			echo "  ✅ Started (PID $$(cat $(PID_FILE)))"; \
			echo "  🌐 http://localhost:$(APP_PORT)"; \
			echo "  📜 make logs   # tail $(LOG_FILE)"; \
			echo "  🛑 make off    # stop"; \
		else \
			echo "  ❌ Streamlit failed to start. Last lines of $(LOG_FILE):"; \
			tail -n 20 $(LOG_FILE) 2>/dev/null || true; \
			rm -f $(PID_FILE); \
			exit 1; \
		fi; \
	fi

off: ## Turn the app OFF — stop the background Streamlit
	$(call banner,Stopping Streamlit)
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID 2>/dev/null && echo "  ✅ Stopped (PID $$PID)"; \
		else \
			echo "  PID file present but process $$PID is not running."; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "  No PID file — looking for orphans on :$(APP_PORT)…"; \
		PIDS=$$(lsof -ti :$(APP_PORT) 2>/dev/null || true); \
		if [ -n "$$PIDS" ]; then \
			kill $$PIDS && echo "  ✅ Killed orphaned PIDs: $$PIDS"; \
		else \
			echo "  Nothing to stop."; \
		fi; \
	fi

restart: off on ## Restart the app (off + on)

logs: ## Tail the background app log (Ctrl+C to stop tailing)
	@test -f $(LOG_FILE) && tail -f $(LOG_FILE) || echo "  No log file. App not started? Try 'make on'."

app: ## Run Streamlit in the FOREGROUND (Ctrl+C stops it)
	$(call banner,Launching Streamlit app on :$(APP_PORT) [foreground])
	$(STREAMLIT) run app.py --server.port $(APP_PORT)

# =============================================================================
##@ COMPOSITE PIPELINES — end-to-end shortcuts
# =============================================================================

.PHONY: pipeline defense

pipeline: train-rf-no-history walk-forward portfolios ## Retrain best model → backtest → portfolios (reuses run data)
	@echo ""
	@echo "✅ Pipeline complete. Run 'make app' to launch the defense demo."

defense: pipeline on ## Pipeline + turn the app ON (Step 5 deliverable)

# =============================================================================
##@ QUALITY — verify the project still works
# =============================================================================

.PHONY: lint format syntax-check

syntax-check: ## Quick byte-compile sanity check across all .py
	$(call banner,Compiling Python sources)
	$(PYTHON) -m compileall -q app.py fetch_data.py src models

lint: ## Lint with ruff if installed (no-op otherwise)
	@command -v $(VENV)/bin/ruff >/dev/null 2>&1 \
		&& $(VENV)/bin/ruff check app.py fetch_data.py src models \
		|| echo "  ruff not installed — skipping (pip install ruff to enable)"

format: ## Auto-format with ruff if installed
	@command -v $(VENV)/bin/ruff >/dev/null 2>&1 \
		&& $(VENV)/bin/ruff format app.py fetch_data.py src models \
		|| echo "  ruff not installed — skipping (pip install ruff to enable)"

# =============================================================================
##@ CLEAN — reversible cleanup, increasing aggression
# =============================================================================

.PHONY: clean clean-models clean-all distclean

clean: ## Remove __pycache__, .pyc, app PID/log
	$(call banner,Cleaning Python caches)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f $(PID_FILE) $(LOG_FILE)
	@echo "✅ Caches cleaned."

clean-models: ## Delete model artifacts in the ACTIVE RUN (CSV/pkl/json/pt) — re-train rebuilds
	$(call banner,Removing model artifacts from active run)
	rm -f $(MODELS_DIR)/*.pkl $(MODELS_DIR)/*.pt $(MODELS_DIR)/*.json \
	      $(MODELS_DIR)/model_metrics.csv $(MODELS_DIR)/predictions.csv \
	      $(MODELS_DIR)/latest_rankings.csv \
	      $(MODELS_DIR)/random_forest_*.csv \
	      $(MODELS_DIR)/xgboost_*.csv \
	      $(MODELS_DIR)/rocm_*.csv \
	      $(MODELS_DIR)/walk_forward_*.csv \
	      $(MODELS_DIR)/portfolio_*.csv
	@echo "✅ Model artifacts removed (re-run 'make pipeline' to rebuild)."

clean-all: clean ## Caches (does NOT delete data, models, or .venv)
	@echo "✅ Caches cleaned. data/models/.venv kept."

distclean: clean ## Nuclear: clean + remove ../.venv
	$(call banner,Removing ../.venv)
	rm -rf $(VENV)
	@echo "✅ venv removed. Run 'make setup' to rebuild."

# =============================================================================
##@ STATUS — quick overview of what's been built
# =============================================================================

.PHONY: status

status: ## Show what's present (venv, data, models, reports)
	@echo ""
	@echo "📦 Environment"
	@test -x $(PYTHON) && echo "  venv:    ✅ $(PYTHON) ($$($(PYTHON) --version))" || echo "  venv:    ❌ missing (run: make setup)"
	@echo ""
	@echo "📈 Data (active run via endproduct/data)"
	@test -f $(DATA_DIR)/prices_long.csv && echo "  prices:  ✅ $(DATA_DIR)/prices_long.csv ($$(du -hL $(DATA_DIR)/prices_long.csv | cut -f1))" || echo "  prices:  ❌ missing (check symlink)"
	@test -f $(DATA_DIR)/tickers.csv && echo "  tickers: ✅ present" || echo "  tickers: ❌ missing"
	@echo ""
	@echo "🤖 Models (active run via endproduct/models)"
	@test -f $(MODELS_DIR)/random_forest_no_history_model.pkl && echo "  best RF: ✅ present" || echo "  best RF: ❌ missing (run: make train-rf-no-history)"
	@test -f $(MODELS_DIR)/walk_forward_rf_no_history_summary.csv && echo "  walk-fw: ✅ summary present" || echo "  walk-fw: ❌ missing (run: make walk-forward)"
	@test -f $(MODELS_DIR)/portfolio_recommendations.csv && echo "  ports:   ✅ portfolio_recommendations.csv" || echo "  ports:   ❌ missing (run: make portfolios)"
	@echo ""
	@echo "📄 Reports"
	@ls $(RENDERING1_DIR)/*.pdf 2>/dev/null | sed 's|^|  |' || echo "  (no PDFs yet — run: make report-pdf)"
	@echo ""
