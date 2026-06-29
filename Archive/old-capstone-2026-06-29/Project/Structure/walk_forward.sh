#!/usr/bin/env bash
# Walk-forward backtest of the production model — Bash loop + Python per fold.
#
# Expanding-window scheme (same as the legacy RF backtest): start with 504
# trading days of training, test the next 63, step forward 63. Each fold trains
# XGBoost with the FIXED best_params.json from `make train` (no per-fold Optuna
# retuning -> fast and leak-free), and appends its metrics row. The folds are
# then loaded into liora.duckdb (walk_forward_folds + walk_forward_summary).
#
# Run from Project/Structure:  ./walk_forward.sh   (or: make walk-forward)
set -euo pipefail
cd "$(dirname "$0")"

PY=../.venv/bin/python
PARAMS=../endproduct/models/best_params.json
OUT="$(mktemp /tmp/wf_folds.XXXXXX.csv)"
trap 'rm -f "$OUT"' EXIT

[ -f "$PARAMS" ] || { echo "Missing $PARAMS — run 'make train' first." >&2; exit 1; }

echo "▶ Walk-forward folds (expanding window: init=504, test=63, step=63)"

# Emit "fold train_end test_end" lines from the DuckDB trading calendar.
fold_boundaries() {
  "$PY" - <<'PYEOF'
from src.db import connect
dates = [r[0] for r in connect(True).execute(
    "SELECT DISTINCT date FROM ohlcv ORDER BY date").fetchall()]
INIT, WIN, STEP = 504, 63, 63
fold, i = 1, INIT
while i + WIN <= len(dates):
    print(fold, dates[i - 1], dates[i + WIN - 1])
    fold += 1
    i += STEP
PYEOF
}

while read -r fold train_end test_end; do
  "$PY" train_xgb_optuna.py --mode fold \
      --train-end "$train_end" --test-end "$test_end" \
      --params "$PARAMS" --fold "$fold" --out "$OUT"
done < <(fold_boundaries)

echo "▶ Loading folds → DuckDB (walk_forward_folds + walk_forward_summary)"
WF_OUT="$OUT" "$PY" - <<'PYEOF'
import os
import pandas as pd
from src.db import connect

folds = pd.read_csv(os.environ["WF_OUT"]).sort_values("fold")
con = connect(read_only=False)
con.register("_folds", folds)
con.execute("CREATE OR REPLACE TABLE walk_forward_folds AS SELECT * FROM _folds")

summary = pd.DataFrame([{
    "model": "xgboost_no_history",
    "folds": int(len(folds)),
    "mean_mae": float(folds["mae"].mean()),
    "mean_rmse": float(folds["rmse"].mean()),
    "mean_spearman_rank_corr": float(folds["spearman_rank_corr"].mean()),
    "mean_universe_avg_actual_return": float(folds["universe_avg_actual_return"].mean()),
    "mean_top5_avg_actual_return": float(folds["top5_avg_actual_return"].mean()),
    "mean_top10_avg_actual_return": float(folds["top10_avg_actual_return"].mean()),
    "positive_top5_folds": int((folds["top5_avg_actual_return"] > 0).sum()),
}])
con.register("_summary", summary)
con.execute("CREATE OR REPLACE TABLE walk_forward_summary AS SELECT * FROM _summary")

# Walk-forward feature-importance panel: reuse the production model's gains
# (same fixed hyperparameters drive every fold).
con.execute(
    "CREATE OR REPLACE TABLE walk_forward_feature_importance AS "
    "SELECT feature, importance FROM feature_importance "
    "WHERE model_key = 'xgboost_no_history' ORDER BY importance DESC"
)
con.close()
print(summary.to_string(index=False))
PYEOF
echo "✅ Walk-forward complete."
