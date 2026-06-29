# Minimal per-asset pipeline. One operator surface.
#   make deps                 install requirements into ../.venv
#   make build-db             data/seed/*_ohlcv_1h.parquet -> liora.duckdb
#   make run-asset TICKER=AAPL   run the notebook -> Assets/AAPL/ (7 files)
#   make feature-search       rank feature combos per ticker on Train CV AUC-PR (OOS untouched)
#   make loop "AAPL TSLA XOM" per-ticker end-to-end: top Train features + Kelly (search->apply->run->dashboard)
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
SP500_DUCKDB := /opt/to_liora_school/qc-raw-ohlcv-data-sp500-alpaca/endproduct/ohlcv_1h_sp500_alpaca.duckdb

# `make loop "AAPL TSLA XOM"` (== `make loop AAPL TSLA XOM`), or `make loop TICKERS="AAPL TSLA XOM"`, or bare `make loop`.
LOOP_TICKERS := $(strip $(if $(TICKERS),$(TICKERS),$(filter-out loop,$(MAKECMDGOALS))))
ifeq ($(strip $(LOOP_TICKERS)),)
LOOP_TICKERS := AAPL TSLA XOM
endif
ifeq (loop,$(firstword $(MAKECMDGOALS)))
$(eval $(filter-out loop,$(MAKECMDGOALS)):;@:)   # ticker args become no-op goals (no "No rule to make target" error)
endif

.PHONY: deps build-db run-asset feature-search loop dashboard serve on off restart logs clean help

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

deps:
	$(PIP) install -r requirements.txt

build-db:
	$(PY) build_db.py

run-asset:
	@test -n "$(TICKER)" || (echo "usage: make run-asset TICKER=AAPL" && exit 1)
	$(PY) run_asset.py TICKER=$(TICKER)

# Train-only feature-combination search (purged walk-forward CV AUC-PR; OOS is NEVER read).
# Shared by `feature-search` (print-only) and `loop` (apply config + run). Env vars:
#   LOOP_TICKERS (space list, default "AAPL TSLA XOM"); LOOP_APPLY=1 -> write asset_overrides;
#   LOOP_ENSURE_SEED=1 -> export a missing data/seed/<T>_ohlcv_1h.parquet from SP500_DUCKDB.
define FEATURE_SEARCH_PY
import os, sys, copy, json
sys.path.insert(0, ".")
import numpy as np, pandas as pd, xgboost as xgb
import pipeline as P
SEED = P.seed_everything()
FB = dict(P.XGBOOST_OPTUNA_SEARCH_SPACE["fallback_params"])
TICKERS = os.environ.get("LOOP_TICKERS", "AAPL TSLA XOM").split()
APPLY = bool(os.environ.get("LOOP_APPLY"))
ENSURE = bool(os.environ.get("LOOP_ENSURE_SEED"))
SP500_DUCKDB = os.environ.get("SP500_DUCKDB", "")
COMBOS = [
  ("1h", [], None, None, None),
  ("1h+F9 (default)", [9], None, None, None),
  ("1h+F9 +1d", [9], [], None, None),
  ("1h+F9 +1d+F109", [9], [109], None, None),
  ("1h+F9 +1w", [9], None, [], None),
  ("1h+F9 +1w+F209", [9], None, [209], None),
  ("1h+F9 +1d +1w", [9], [], [], None),
  ("1h+F9 +1d+F109 +1w+F209", [9], [109], [209], None),
  ("1h+1d (no F9)", [], [], None, None),
  ("1h+F9 +1d +cross", [9], [], None, []),
  ("1h+F9 +1d+1w +cross", [9], [], [], []),
  ("1h+F9 +1d+1w +cross+F909+F910", [9], [], [], [909, 910]),
]
def ensure_seed(T):
  p = "data/seed/%s_ohlcv_1h.parquet" % T
  if os.path.exists(p):
    return
  if not ENSURE:
    raise SystemExit("missing seed %s (add it to data/seed/, or run via `make loop`)" % p)
  if not SP500_DUCKDB or not os.path.exists(SP500_DUCKDB):
    raise SystemExit("missing seed %s and SP500_DUCKDB unavailable (%s)" % (p, SP500_DUCKDB))
  import duckdb
  con = duckdb.connect(SP500_DUCKDB, read_only=True)
  d = con.execute("select ts as timestamp, open, high, low, close, volume from ohlcv_1h where symbol=? order by ts", [T]).fetchdf()
  con.close()
  if d.empty:
    raise SystemExit("ticker %s not found in %s" % (T, SP500_DUCKDB))
  d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.tz_localize("America/New_York", ambiguous="infer", nonexistent="shift_forward").dt.tz_convert("UTC")
  d["volume"] = d["volume"].astype("float64")
  d = d[["timestamp", "open", "high", "low", "close", "volume"]]
  os.makedirs("data/seed", exist_ok=True)
  d.to_parquet(p, index=False)
  print("  exported seed %s (%d bars) from SP500 DuckDB" % (T, len(d)))
def manifest(a1h, a1d, a1w, abt):
  c = copy.deepcopy(P.PER_ASSET_FEATURE_SELECTION)
  c["asset_overrides"] = {}
  c["defaults"] = {
    "1h": {"enabled": True, "additional_feature_ids": a1h},
    "1d": {"enabled": a1d is not None, "additional_feature_ids": a1d or []},
    "1w": {"enabled": a1w is not None, "additional_feature_ids": a1w or []},
    "between_timeframes": {"enabled": abt is not None, "additional_feature_ids": abt or []},
  }
  return P.resolve_feature_manifest(None, cfg=c)
def cv_aucpr(df_b, b, names):
  X = df_b[names].to_numpy(float)
  y = df_b["Y_outcome"].to_numpy(int)
  w = df_b["label_uniqueness_weight"].to_numpy(float)
  t0s = [int(s.split(":")[1]) for s in df_b["setup_id"]]
  ap = []
  for tr, va in P.purged_wf_folds(t0s, b["train_start_idx"], b["train_end_idx"]):
    bst = P._xgb_train(X[tr], y[tr], w[tr], FB, SEED, feature_names=names)
    ap.append(P.average_precision(y[va], bst.predict(xgb.DMatrix(X[va], feature_names=names))))
  return float(np.mean(ap)) if ap else float("nan")
print("Feature search - Train-only purged walk-forward CV AUC-PR (0.5 = random). OOS is NEVER read.")
winners = {}
for T in TICKERS:
  ensure_seed(T)
  df = pd.read_parquet("data/seed/%s_ohlcv_1h.parquet" % T)
  sup = P.derive_output_b(df, T, manifest([9], [109], [209], None))   # superset 1h+1d+1w (no cross), once
  rows = []
  for label, a1h, a1d, a1w, abt in COMBOS:
    m = manifest(a1h, a1d, a1w, abt)
    names = m["effective_feature_names"]
    rec = sup if abt is None else P.derive_output_b(df, T, m)          # subset for non-cross; rebuild for cross
    rows.append((cv_aucpr(rec["df_b"], rec["bounds"], names), len(names), label, (a1h, a1d, a1w, abt)))
  rows.sort(key=lambda r: (-(r[0] if r[0] == r[0] else -9.0), r[1]))
  print("\n=== %s (%d train setups) ===" % (T, sup["df_b"].shape[0]))
  for s, nf, label, _ in rows:
    print("  CV=%.4f  [%2df]  %s" % (s, nf, label))
  a1h, a1d, a1w, abt = rows[0][3]
  ov = {"1h": {"enabled": True, "additional_feature_ids": a1h}}
  if a1d is not None: ov["1d"] = {"enabled": True, "additional_feature_ids": a1d}
  if a1w is not None: ov["1w"] = {"enabled": True, "additional_feature_ids": a1w}
  if abt is not None: ov["between_timeframes"] = {"enabled": True, "additional_feature_ids": abt}
  winners[T] = ov
  print("  WINNER: %s (CV %.4f)  ->  asset_overrides[%s] = %s" % (rows[0][2], rows[0][0], T, json.dumps(ov)))
if APPLY:
  cfgp = "config/per_asset_feature_selection.json"
  cfg = json.loads(open(cfgp).read())
  cfg.setdefault("asset_overrides", {})
  for T, ov in winners.items():
    cfg["asset_overrides"][T] = ov
  tmp = cfgp + ".tmp"
  open(tmp, "w").write(json.dumps(cfg, indent=2) + "\n")
  os.replace(tmp, cfgp)
  print("\napplied %d override(s) -> %s" % (len(winners), cfgp))
endef
export FEATURE_SEARCH_PY

feature-search:
	@$(PY) -c "$$FEATURE_SEARCH_PY"

# End-to-end per ticker: top Train features (CV AUC-PR) -> apply config -> build-db -> run-asset (Optuna + Kelly + OOS) -> dashboard.
loop:
	@echo "loop tickers: $(LOOP_TICKERS)"
	@LOOP_TICKERS="$(LOOP_TICKERS)" LOOP_APPLY=1 LOOP_ENSURE_SEED=1 SP500_DUCKDB="$(SP500_DUCKDB)" $(PY) -c "$$FEATURE_SEARCH_PY"
	$(PY) build_db.py
	@for T in $(LOOP_TICKERS); do echo ">>> run-asset $$T"; $(PY) run_asset.py TICKER=$$T || exit 1; done
	python3 build_dashboard.py

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
