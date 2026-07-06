# 10000-xgb-lstm-liora — unified operator surface for the two vendored pipelines.
#   make deps          one .venv at the root + pinned requirements (serves xgb/ + lstm/ + the app)
#   make app           the shared ML Basket Simulator (Streamlit) on :8503 — dropdown XGBoost/LSTM
#   make verify-xgb    reproduce the XGBoost demo tickers from xgb/'s bundled mini-bars == sealed rows
#   make verify-lstm   reproduce a diverse LSTM sample from lstm/'s committed manifest == sealed rows
#   make clean         remove per-asset run scratch in both subprojects (keeps the sealed data)
#   --- WO-FS feature-selection study (fs/); UNIVERSE=demo (default) | full ---
#   make fs-test       run all WO-FS gates (anti-lookahead, scaler leak, purge/embargo, CPCV, unit)
#   make fs-study1     calibrate + freeze the shared 3-class labels (Optuna Study 1)
#   make fs-xgb        XGBoost loop: elimination -> stability -> Study 2 -> CPCV -> SHAP
#   make fs-lstm       LSTM loop: channel elimination -> stability -> Study 2 -> CPCV -> SHAP
#   make fs-holdout-xgb / fs-holdout-lstm   the ONE holdout read per model (guarded)
#   make fs-all        study1 + fs-xgb + fs-lstm (no holdout — run that deliberately)
#   make fs-warm       parallel feature-cache warm-up (all cores) for the whole universe
#   make fs-search-on  DETACHED convergence optimizer over the FULL universe (survives logout)
#   make fs-search-off / fs-search-status   stop / inspect the detached optimizer
PY := .venv/bin/python3
ST := .venv/bin/streamlit
APP_PORT ?= 8503
UNIVERSE ?= demo
FS_PID := logs/fs-search.pid
FS_LOG := logs/fs-search.log

.PHONY: deps app verify-xgb verify-lstm clean help \
        fs-test fs-study1 fs-xgb fs-lstm fs-holdout-xgb fs-holdout-lstm fs-all \
        fs-warm fs-search-on fs-search-off fs-search-status
help:
	@grep -E '^#   make|^#   ---' Makefile | sed 's/^#   //'

deps:
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@# make the shared venv visible to each subproject (their Makefiles expect a local .venv)
	@ln -sfn ../.venv xgb/.venv 2>/dev/null || true
	@ln -sfn ../.venv lstm/.venv 2>/dev/null || true

app:
	$(ST) run app/app.py --server.port $(APP_PORT)

verify-xgb:
	@cd xgb && ../$(PY) tools/verify_repro.py $(TICKERS)

verify-lstm:
	@cd lstm && ../$(PY) tools/verify_repro.py $(TICKERS)

fs-test:
	$(PY) -m fs.tests

fs-study1:
	$(PY) -m fs.xgb_loop --universe $(UNIVERSE) --stage study1

fs-xgb:
	$(PY) -m fs.xgb_loop --universe $(UNIVERSE) --stage all

fs-lstm:
	$(PY) -m fs.lstm_loop --universe $(UNIVERSE) --stage all

fs-holdout-xgb:
	$(PY) -m fs.xgb_loop --universe $(UNIVERSE) --stage holdout

fs-holdout-lstm:
	$(PY) -m fs.lstm_loop --universe $(UNIVERSE) --stage holdout

fs-all: fs-study1 fs-xgb fs-lstm

fs-warm:
	$(PY) -m fs.warm --universe $(UNIVERSE)

# Detached 8h optimizer: setsid+nohup so it survives the terminal closing; PID in a file for stop.
fs-search-on:
	@mkdir -p logs
	@if [ -f $(FS_PID) ] && kill -0 $$(cat $(FS_PID)) 2>/dev/null; then \
		echo "already running (PID $$(cat $(FS_PID))) — make fs-search-off first"; exit 1; fi
	@setsid nohup $(PY) -m fs.supervise --universe $(UNIVERSE) >> $(FS_LOG) 2>&1 & echo $$! > $(FS_PID)
	@sleep 1; echo "fs-search started (PID $$(cat $(FS_PID))), UNIVERSE=$(UNIVERSE) -> $(FS_LOG)"

fs-search-off:
	@if [ -f $(FS_PID) ]; then kill -- -$$(cat $(FS_PID)) 2>/dev/null; kill $$(cat $(FS_PID)) 2>/dev/null; \
		rm -f $(FS_PID); echo "stopped"; else echo "not running"; fi

fs-search-status:
	@if [ -f $(FS_PID) ] && kill -0 $$(cat $(FS_PID)) 2>/dev/null; then \
		echo "RUNNING (PID $$(cat $(FS_PID)))"; else echo "not running"; fi
	@test -f fs/artifacts/$(UNIVERSE)/supervisor_progress.json && \
		$(PY) -c "import json;p=json.load(open('fs/artifacts/$(UNIVERSE)/supervisor_progress.json'));print('last:',p.get('last'))" || true
	@echo "--- tail $(FS_LOG) ---"; tail -n 12 $(FS_LOG) 2>/dev/null || echo "(no log yet)"

clean:
	rm -rf xgb/Assets/*/ lstm/Assets/*/ */__pycache__ */*/__pycache__ .ipynb_checkpoints
