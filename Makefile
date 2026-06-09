# =============================================================================
# Stocks Recommender Based on User Profile — Liora ML Engineering project
#
# Single entry point for the whole pipeline:
#   setup → data → EDA/report → modeling (stages 1–7) → portfolios → app
#
# Quick start:
#   make            # show this help
#   make setup      # create .venv and install all deps
#   make pipeline   # fetch → train best model → walk-forward → portfolios
#   make app        # run the Streamlit defense demo
# =============================================================================

# --- config -----------------------------------------------------------------
SHELL          := /bin/bash
.SHELLFLAGS    := -eu -o pipefail -c
.DEFAULT_GOAL  := help

VENV           ?= .venv
PYTHON         ?= ./$(VENV)/bin/python
PIP            ?= ./$(VENV)/bin/pip
STREAMLIT      ?= ./$(VENV)/bin/streamlit

# Absolute paths — needed when we `cd` into a subdir (e.g. mac-2026-06-08)
ABS_PYTHON     := $(abspath $(PYTHON))
ABS_STREAMLIT  := $(abspath $(STREAMLIT))

ROOT_REQ       := requirements.txt
MAC_DIR        := mac-2026-06-08
MAC_REQ        := $(MAC_DIR)/requirements.txt
MODELS_DIR     := $(MAC_DIR)/models
REPORTS_DIR    := reports
DATA_DIR       := data

# Defense demo data snapshot — model results read from here
MODEL_EXPORT   := $(MODELS_DIR)

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

$(VENV)/bin/python: ## (internal) create the virtualenv
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV)/bin/python ## Create .venv (no deps installed)

install: $(VENV)/bin/python ## Install root requirements (app + EDA)
	$(call banner,Installing root requirements)
	$(PIP) install -r $(ROOT_REQ)

install-mac: $(VENV)/bin/python ## Install modeling extras (sklearn, xgboost, ROCm torch)
	$(call banner,Installing modeling requirements ($(MAC_REQ)))
	$(PIP) install -r $(MAC_REQ)

install-all: install install-mac ## Install root + modeling requirements

setup: install-all ## Full setup: venv + all dependencies
	@echo "✅ Environment ready. Next: make fetch (or make fetch-smoke for a quick check)."

freeze: ## Snapshot the active venv into requirements.lock.txt
	$(PIP) freeze > requirements.lock.txt
	@echo "✅ Wrote requirements.lock.txt"

# =============================================================================
##@ STEP 1 — Data mining (acquisition from Alpaca)
# =============================================================================

.PHONY: fetch fetch-smoke fetch-mac data-check

fetch: ## Download full S&P 500 OHLCV via Alpaca (~10y, 8–10 min)
	$(call banner,Fetching S&P 500 from Alpaca [full run])
	$(PYTHON) fetch_data.py $(FETCH_ARGS)

fetch-smoke: ## Quick smoke test: fetch 20 tickers only
	$(call banner,Fetching S&P 500 from Alpaca [smoke: 20 tickers])
	$(PYTHON) fetch_data.py --limit 20

fetch-mac: ## 5-year fetch for the modeling pipeline (mac export)
	$(call banner,Fetching 5y window for modeling pipeline)
	cd $(MAC_DIR) && $(ABS_PYTHON) fetch_data.py --years 5 --batch-size 10

data-check: ## Print row counts / date ranges from data/
	$(call banner,Data inventory)
	@ls -lh $(DATA_DIR)/*.csv $(DATA_DIR)/*.duckdb 2>/dev/null || echo "  (no data files yet — run 'make fetch')"
	@$(PYTHON) -c "import pandas as pd, pathlib; \
p=pathlib.Path('$(DATA_DIR)/prices_long.csv'); \
print('prices_long.csv: missing') if not p.exists() else \
(lambda d: print(f'  rows={len(d):,}  tickers={d.ticker.nunique()}  date={d.date.min()}→{d.date.max()}'))(pd.read_csv(p, parse_dates=['date']))" 2>/dev/null || true

# =============================================================================
##@ STEP 2 — Pre-processing & figures → Rendering 1 (PDF)
# =============================================================================

.PHONY: figures report-pdf report

figures: ## Regenerate EDA figures used in REPORT.md
	$(call banner,Building report figures)
	cd $(REPORTS_DIR) && $(ABS_PYTHON) make_figures.py

report-pdf: ## Build reports/REPORT.pdf via pandoc + xelatex
	$(call banner,Building reports/REPORT.pdf)
	cd $(REPORTS_DIR) && ./build_pdf.sh

report: figures report-pdf ## Figures + PDF in one shot

# =============================================================================
##@ STEP 3 — Modeling (stages 1–6 + builder)
# =============================================================================

.PHONY: train-baseline train-rf train-rf-no-history train-xgboost train-rocm \
        train-all walk-forward

train-baseline: ## Stage 1 — Ridge linear baseline
	$(call banner,Training Ridge baseline [Stage 1])
	cd $(MAC_DIR) && $(ABS_PYTHON) models/train_first_model.py

train-rf: ## Stage 2 — Random Forest
	$(call banner,Training Random Forest [Stage 2])
	cd $(MAC_DIR) && $(ABS_PYTHON) models/train_random_forest_model.py

train-rf-no-history: ## Stage 4 — RF without history_days (current best)
	$(call banner,Training Random Forest no-history [Stage 4 — BEST])
	cd $(MAC_DIR) && $(ABS_PYTHON) models/train_random_forest_no_history_model.py

train-xgboost: ## Stage 5 — XGBoost comparison
	$(call banner,Training XGBoost no-history [Stage 5])
	cd $(MAC_DIR) && $(ABS_PYTHON) models/train_xgboost_no_history_model.py

train-rocm: ## Stage 3.3 — ROCm PyTorch (AMD GPU deep learning)
	$(call banner,Training ROCm PyTorch model [Stage 3.3 — DL])
	cd $(MAC_DIR) && HSA_ENABLE_DXG_DETECTION=1 $(ABS_PYTHON) models/train_rocm_model.py

train-all: train-baseline train-rf train-rf-no-history train-xgboost train-rocm ## All 5 models, in order

walk-forward: ## Stage 6 — walk-forward backtest on RF no-history
	$(call banner,Walk-forward backtest [Stage 6])
	cd $(MAC_DIR) && $(ABS_PYTHON) models/walk_forward_random_forest_no_history.py

# =============================================================================
##@ STEP 3.x — Portfolio construction
# =============================================================================

.PHONY: portfolios

portfolios: ## Stage 7 — build conservative / balanced / aggressive portfolios
	$(call banner,Building portfolios [Stage 7])
	cd $(MAC_DIR) && $(ABS_PYTHON) models/build_portfolios.py
	@echo ""
	@echo "📊 Portfolio outputs:"
	@ls -lh $(MODELS_DIR)/portfolio_*.csv 2>/dev/null || true

# =============================================================================
##@ STEP 5 — Streamlit defense demo (on / off / restart / logs)
# =============================================================================

.PHONY: on off restart logs app app-mac

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

app-mac: ## Run the mac-export Streamlit app variant (foreground)
	$(call banner,Launching mac-export Streamlit app on :$(APP_PORT))
	cd $(MAC_DIR) && $(ABS_STREAMLIT) run app.py --server.port $(APP_PORT)

# =============================================================================
##@ COMPOSITE PIPELINES — end-to-end shortcuts
# =============================================================================

.PHONY: pipeline pipeline-quick defense

pipeline: fetch-mac train-rf-no-history walk-forward portfolios ## Full data → best model → backtest → portfolios
	@echo ""
	@echo "✅ Pipeline complete. Run 'make app' to launch the defense demo."

pipeline-quick: train-rf-no-history walk-forward portfolios ## Reuse existing data; rerun model → backtest → portfolios
	@echo "✅ Quick re-run complete (data was not re-fetched)."

defense: pipeline on ## Pipeline + turn the app ON (Step 5 deliverable)

# =============================================================================
##@ QUALITY — verify the project still works
# =============================================================================

.PHONY: lint format syntax-check

syntax-check: ## Quick byte-compile sanity check across all .py
	$(call banner,Compiling Python sources)
	$(PYTHON) -m compileall -q app.py fetch_data.py src $(MAC_DIR)

lint: ## Lint with ruff if installed (no-op otherwise)
	@command -v $(VENV)/bin/ruff >/dev/null 2>&1 \
		&& $(VENV)/bin/ruff check app.py fetch_data.py src $(MAC_DIR) \
		|| echo "  ruff not installed — skipping (pip install ruff to enable)"

format: ## Auto-format with ruff if installed
	@command -v $(VENV)/bin/ruff >/dev/null 2>&1 \
		&& $(VENV)/bin/ruff format app.py fetch_data.py src $(MAC_DIR) \
		|| echo "  ruff not installed — skipping (pip install ruff to enable)"

# =============================================================================
##@ CLEAN — reversible cleanup, increasing aggression
# =============================================================================

.PHONY: clean clean-data clean-models clean-reports clean-all

clean: ## Remove __pycache__, dashboard.html, .pyc, app PID/log
	$(call banner,Cleaning Python caches)
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "./$(VENV)/*" -delete 2>/dev/null || true
	rm -f dashboard.html $(PID_FILE) $(LOG_FILE)
	@echo "✅ Caches cleaned."

clean-data: ## Delete generated CSVs in data/ (keeps duckdb stores)
	$(call banner,Removing generated CSVs)
	rm -f $(DATA_DIR)/tickers.csv $(DATA_DIR)/prices_long.csv \
	      $(DATA_DIR)/prices_close_wide.csv $(DATA_DIR)/failed_tickers.csv
	rm -rf $(DATA_DIR)/by_ticker
	@echo "✅ Data CSVs removed (duckdb files kept)."

clean-models: ## Delete model artifacts (CSV/pkl/json/pt) — re-train will rebuild
	$(call banner,Removing model artifacts)
	rm -f $(MODELS_DIR)/*.pkl $(MODELS_DIR)/*.pt $(MODELS_DIR)/*.json \
	      $(MODELS_DIR)/model_metrics.csv $(MODELS_DIR)/predictions.csv \
	      $(MODELS_DIR)/latest_rankings.csv \
	      $(MODELS_DIR)/random_forest_*.csv \
	      $(MODELS_DIR)/xgboost_*.csv \
	      $(MODELS_DIR)/rocm_*.csv \
	      $(MODELS_DIR)/walk_forward_*.csv \
	      $(MODELS_DIR)/portfolio_*.csv
	@echo "✅ Model artifacts removed."

clean-reports: ## Remove non-milestone report PDFs (keeps report_v*.pdf)
	$(call banner,Removing scratch report PDFs)
	find $(REPORTS_DIR) -maxdepth 1 -name "*.pdf" -not -name "report_v*.pdf" -delete
	@echo "✅ Scratch PDFs removed (milestone report_v*.pdf kept)."

clean-all: clean clean-data ## Caches + generated data (does NOT delete .venv or models)
	@echo "✅ Full clean done. .venv and models kept — use 'make distclean' to nuke everything."

distclean: clean-all clean-models ## Nuclear: clean-all + remove models + .venv
	$(call banner,Removing .venv)
	rm -rf $(VENV)
	@echo "✅ Project fully reset. Run 'make setup' to rebuild."

# =============================================================================
##@ STATUS — quick overview of what's been built
# =============================================================================

.PHONY: status

status: ## Show what's present (venv, data, models, reports)
	@echo ""
	@echo "📦 Environment"
	@test -x $(PYTHON) && echo "  venv:    ✅ $(PYTHON) ($$($(PYTHON) --version))" || echo "  venv:    ❌ missing (run: make setup)"
	@echo ""
	@echo "📈 Data"
	@test -f $(DATA_DIR)/prices_long.csv && echo "  prices:  ✅ $(DATA_DIR)/prices_long.csv ($$(du -h $(DATA_DIR)/prices_long.csv | cut -f1))" || echo "  prices:  ❌ missing (run: make fetch)"
	@test -f $(DATA_DIR)/tickers.csv && echo "  tickers: ✅ $(DATA_DIR)/tickers.csv" || echo "  tickers: ❌ missing"
	@ls $(DATA_DIR)/*.duckdb 2>/dev/null | sed 's|^|  duckdb:  ✅ |' || echo "  duckdb:  (none)"
	@echo ""
	@echo "🤖 Models"
	@test -f $(MODELS_DIR)/random_forest_no_history_model.pkl && echo "  best RF: ✅ $(MODELS_DIR)/random_forest_no_history_model.pkl" || echo "  best RF: ❌ missing (run: make train-rf-no-history)"
	@test -f $(MODELS_DIR)/walk_forward_rf_no_history_summary.csv && echo "  walk-fw: ✅ summary present" || echo "  walk-fw: ❌ missing (run: make walk-forward)"
	@test -f $(MODELS_DIR)/portfolio_recommendations.csv && echo "  ports:   ✅ portfolio_recommendations.csv" || echo "  ports:   ❌ missing (run: make portfolios)"
	@echo ""
	@echo "📄 Reports"
	@ls $(REPORTS_DIR)/*.pdf 2>/dev/null | sed 's|^|  |' || echo "  (no PDFs yet — run: make report-pdf)"
	@echo ""
