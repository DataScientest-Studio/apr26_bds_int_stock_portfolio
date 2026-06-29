"""Stocks Recommender Based on User Profile — Streamlit defense demo.

Multi-page app that surfaces the whole project: data, audit, EDA, models,
feature importance, walk-forward backtest, rankings and the precomputed
portfolios. NOTHING is trained at runtime — every page reads precomputed
CSV/JSON only.

Single data source: the active run (Alpaca S&P 500, 503 tickers) under
Archive/runs/<active_run>, reached via Project/endproduct/ symlinks. Both the
EDA/audit pages and the model/portfolio pages read the same run.

Run (from Project/Structure):
    make app          # or: ../.venv/bin/streamlit run app.py
"""

import streamlit as st

from src.data_loader import (
    compute_root_audit,
    load_prices,
    load_prices_wide,
    load_tickers,
)
from src import model_loader as ml
from src import model_plots as mp
from src.paths import ACTIVE_RUN
from src.plots import (
    get_price_line_summary,
    plot_correlation_heatmap,
    plot_price_line,
    plot_return_hist,
    plot_risk_return_scatter,
    plot_sector_count,
    plot_volume_box,
)

st.set_page_config(page_title="Stocks Recommender Based on User Profile", layout="wide")

RUN_NOTE = (
    f"Active run: **{ACTIVE_RUN}** · Alpaca S&P 500 (503 tickers). "
    "All artifacts are precomputed — **no model is trained in this app.**"
)


# --------------------------------------------------------------------------- #
# Cached loaders (read-only). Heavy prediction files load lazily per model.    #
# --------------------------------------------------------------------------- #
@st.cache_data
def root_tickers():
    return load_tickers()


@st.cache_data
def root_prices():
    return load_prices()


@st.cache_data
def root_wide():
    return load_prices_wide()


@st.cache_data
def root_audit():
    return compute_root_audit(root_prices(), root_tickers())


@st.cache_data
def model_metrics():
    return ml.load_model_metrics()


@st.cache_data
def model_predictions(model_key):
    return ml.load_predictions(model_key)


@st.cache_data
def model_rankings(model_key):
    return ml.load_rankings(model_key)


@st.cache_data
def model_importance(model_key):
    return ml.load_feature_importance(model_key)


@st.cache_data
def rocm_history():
    return ml.load_rocm_history()


@st.cache_data
def wf_summary():
    return ml.load_walkforward_summary()


@st.cache_data
def wf_folds():
    return ml.load_walkforward_folds()


@st.cache_data
def wf_importance():
    return ml.load_walkforward_feature_importance()


@st.cache_data
def portfolio_summary():
    return ml.load_portfolio_summary()


@st.cache_data
def portfolio_recs():
    return ml.load_portfolio_recommendations()


@st.cache_data
def portfolio_sectors():
    return ml.load_portfolio_sector_weights()


def pct(value):
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"


def export_banner():
    st.caption(RUN_NOTE)


def missing(name):
    st.warning(f"Artifact not found: `{name}`. This section is unavailable.")


MODEL_LABELS = {key: cfg["label"] for key, cfg in ml.MODELS.items()}


# --------------------------------------------------------------------------- #
# Pages                                                                        #
# --------------------------------------------------------------------------- #
def page_overview():
    st.title("Stocks Recommender Based on User Profile")
    st.caption(
        "A beginner-friendly recommender that turns an investor profile into a "
        "diversified 10-stock portfolio. Decision support — **not** financial advice."
    )

    audit = root_audit()
    summary = portfolio_summary()
    st.caption(RUN_NOTE)

    st.subheader(f"Active dataset · Alpaca S&P 500 (run {ACTIVE_RUN})")
    metrics = model_metrics()
    best = (
        metrics[metrics["model_key"] == ml.PRODUCTION_MODEL_KEY]
        if metrics is not None and not metrics.empty
        else None
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickers", f"{audit['tickers']:,}")
    c2.metric("Price rows", f"{audit['rows']:,}")
    c3.metric("Date range", f"{audit['date_min'].date()} → {audit['date_max'].date()}")
    if best is not None and not best.empty:
        c4.metric(
            "Production model top-5 return",
            pct(best.iloc[0]["top5_avg_actual_return"]),
            help=f"{ml.PRODUCTION_MODEL_KEY} vs universe avg "
            f"{pct(best.iloc[0]['test_universe_avg_actual_return'])}",
        )

    st.divider()
    st.subheader("Pipeline")
    st.markdown(
        "`data (DuckDB) → audit → EDA → SQL features → XGBoost+Optuna → walk-forward → 3 portfolios`\n\n"
        "**Production model:** XGBoost tuned with Optuna — the single live training "
        "pipeline. All 5 models stay on the leaderboard for comparison."
    )

    if summary is not None and not summary.empty:
        st.subheader("Portfolio profiles at a glance")
        st.plotly_chart(mp.plot_portfolio_risk_return(summary), use_container_width=True)

    st.info("No models are trained in this app — everything shown is precomputed.")


def page_data_audit():
    st.title("Data Audit")
    st.caption(f"Quality metrics computed **live** from the active run's dataset · Alpaca S&P 500 (run {ACTIVE_RUN}).")
    audit = root_audit()
    tickers = root_tickers()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickers", f"{audit['tickers']:,}")
    c2.metric("Price rows", f"{audit['rows']:,}")
    c3.metric("Trading dates", f"{audit['trading_dates']:,}")
    c4.metric("Date range", f"{audit['date_min'].date()} → {audit['date_max'].date()}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Duplicate (date,ticker)", f"{audit['duplicates']:,}")
    c6.metric("OHLC violations", f"{audit['ohlc_violations']:,}")
    c7.metric("Zero-volume rows", f"{audit['zero_volume_rows']:,}")

    st.subheader("History length per ticker")
    st.caption(
        f"min {audit['hist_min']} · median {audit['hist_median']:.0f} · max {audit['hist_max']} "
        "trading days. Recent listings (Q, PSKY, SNDK) have the shortest history."
    )
    st.bar_chart(audit["history_per_ticker"].sort_values().reset_index(drop=True))

    st.subheader("Sector distribution")
    st.caption("The recommender enforces a hard 30% max-per-sector cap to offset this imbalance.")
    st.pyplot(plot_sector_count(tickers), clear_figure=True)
    if audit["index_counts"] is not None:
        st.write("Index membership:")
        st.dataframe(audit["index_counts"])

    with st.expander("OHLCV summary statistics"):
        st.dataframe(root_prices()[["open", "high", "low", "close", "adj_close", "volume"]].describe())


def page_eda():
    st.title("EDA — exploratory visualizations")
    tickers = root_tickers()
    prices = root_prices()
    n_rows = len(prices)
    n_tickers = prices["ticker"].nunique()
    n_returns = int(prices["daily_return"].notna().sum())

    st.markdown("**Plot 1 — countplot** (stocks per sector)")
    st.caption("The universe is imbalanced, so a naïve picker would overweight Industrials and Financials.")
    st.pyplot(plot_sector_count(tickers), clear_figure=True)
    with st.expander("🔍 Statistical validation"):
        st.dataframe(tickers["sector"].value_counts())

    st.markdown("**Plot 2 — boxplot** (mean daily volume per stock)")
    st.caption(f"Each point is one of {n_tickers} stocks (mean shares/day). Red dashed line = median.")
    st.pyplot(plot_volume_box(prices), clear_figure=True)
    with st.expander("🔍 Statistical validation"):
        st.dataframe(prices.groupby("ticker")["volume"].mean().describe())

    st.markdown("**Plot 3 — histplot** (daily returns)")
    st.caption(
        f"{n_tickers} stocks × their trading days ≈ {n_rows:,} rows → {n_returns:,} daily returns "
        "(first day per stock dropped). Most mass near 0%, long fat tails."
    )
    st.pyplot(plot_return_hist(prices), clear_figure=True)
    with st.expander("🔍 Statistical validation"):
        st.dataframe(prices["daily_return"].describe())

    st.markdown("**Plot 4 — lineplot** (price over time)")
    st.caption("Adjusted close (USD). Corporate actions already baked in, so the path is comparable over time.")
    ticker = st.selectbox("Choose a ticker", sorted(tickers["ticker"]))
    summary = get_price_line_summary(prices, ticker)
    if summary:
        st.markdown(
            f"**{ticker}** — {summary['n_days']:,} trading days "
            f"({summary['start_date'].date()} → {summary['end_date'].date()}); "
            f"total return **{summary['total_return_pct']:+.0f}%** "
            f"({summary['start_price']:.2f} → {summary['end_price']:.2f} USD)."
        )
    st.pyplot(plot_price_line(prices, ticker), clear_figure=True)

    st.markdown("**Plot 5 — heatmap** (correlation of the 10 most-traded stocks)")
    st.caption("Low cross-correlations justify diversification; the recommender scatters picks across sectors.")
    st.pyplot(plot_correlation_heatmap(prices), clear_figure=True)

    st.markdown("**Plot 6 — scatterplot** (risk vs return)")
    st.caption("X = annualized volatility (risk), Y = annualized return. Dashed lines = medians.")
    st.pyplot(plot_risk_return_scatter(prices), clear_figure=True)
    with st.expander("🔍 Statistical validation"):
        stats = prices.groupby("ticker")["daily_return"].agg(["mean", "std"]).dropna()
        corr = stats["mean"].corr(stats["std"])
        st.write(f"Pearson(risk, return) = `{corr:.4f}` — near 0: blind risk does not guarantee higher return.")


def page_model_leaderboard():
    st.title("Model Leaderboard")
    export_banner()
    metrics = model_metrics()
    if metrics is None or metrics.empty:
        missing("*_metrics.csv")
        return

    st.caption("All 5 models on the same Jan-2025 → Mar-2026 test split.")
    show_cols = [c for c in ["label", "mae", "rmse", "spearman_rank_corr",
                             "test_universe_avg_actual_return", "top5_avg_actual_return"]
                 if c in metrics.columns]
    st.dataframe(metrics[show_cols], use_container_width=True, hide_index=True)

    metric = st.selectbox(
        "Compare on metric",
        ["top5_avg_actual_return", "spearman_rank_corr", "mae", "rmse"],
        format_func=lambda m: mp.METRIC_LABELS.get(m, m),
    )
    st.plotly_chart(mp.plot_metrics_leaderboard(metrics, metric), use_container_width=True)

    if {"top5_avg_actual_return", "test_universe_avg_actual_return"}.issubset(metrics.columns):
        lift = metrics.copy()
        lift["lift_over_universe"] = (
            lift["top5_avg_actual_return"] - lift["test_universe_avg_actual_return"]
        )
        st.markdown("**Top-5 lift over the universe average**")
        st.plotly_chart(mp.plot_metrics_leaderboard(lift, "lift_over_universe"), use_container_width=True)


def page_model_explorer():
    st.title("Model Explorer")
    export_banner()
    model_key = st.selectbox(
        "Model", list(ml.MODELS.keys()),
        index=list(ml.MODELS).index(ml.PRODUCTION_MODEL_KEY),
        format_func=lambda k: MODEL_LABELS[k],
    )

    preds = model_predictions(model_key)
    if preds is None or preds.empty:
        missing(ml.MODELS[model_key]["predictions"])
    else:
        st.subheader("Prediction quality")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(mp.plot_pred_vs_actual(preds), use_container_width=True)
        with col2:
            st.plotly_chart(mp.plot_residual_hist(preds), use_container_width=True)

    st.subheader("Feature importance")
    importance = model_importance(model_key)
    if importance is None:
        st.info("This model does not expose feature importance (linear / neural net).")
    else:
        st.plotly_chart(
            mp.plot_feature_importance_bar(importance, title=f"{MODEL_LABELS[model_key]} — top features"),
            use_container_width=True,
        )
        with st.expander("What do the top features mean?"):
            for feat in importance.head(6)["feature"]:
                st.markdown(f"- **{feat}** — {ml.FEATURE_GLOSSARY.get(feat, 'sector membership dummy.')}")

    if model_key == "random_forest_no_history":
        rf_imp = model_importance("random_forest")
        if rf_imp is not None and importance is not None and st.checkbox("Compare with RF that keeps history_days"):
            st.plotly_chart(
                mp.plot_feature_importance_compare(rf_imp, importance), use_container_width=True
            )
            st.caption("`history_days` dominated the with-history model (~0.45) but was a leak-prone shortcut.")

    if model_key == "pytorch_mlp_rocm":
        history = rocm_history()
        if history:
            st.subheader("Training curve")
            st.plotly_chart(mp.plot_rocm_training_curve(history), use_container_width=True)


def page_walk_forward():
    st.title("Walk-Forward Backtest")
    export_banner()
    summary = wf_summary()
    folds = wf_folds()
    if summary is None or folds is None:
        missing("walk_forward_rf_no_history_*.csv")
        return

    row = summary.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Folds", int(row["folds"]))
    c2.metric("Mean top-5 return", pct(row["mean_top5_avg_actual_return"]))
    c3.metric("Mean universe return", pct(row["mean_universe_avg_actual_return"]))
    c4.metric("Positive top-5 folds", f"{int(row['positive_top5_folds'])} / {int(row['folds'])}")

    st.plotly_chart(mp.plot_walkforward_folds(folds), use_container_width=True)
    with st.expander("Fold-by-fold detail"):
        st.dataframe(folds, use_container_width=True, hide_index=True)

    importance = wf_importance()
    if importance is not None:
        st.subheader("Walk-forward mean feature importance")
        st.plotly_chart(mp.plot_feature_importance_bar(importance), use_container_width=True)


def page_rankings():
    st.title("Rankings")
    export_banner()
    model_key = st.selectbox(
        "Model", list(ml.MODELS.keys()),
        index=list(ml.MODELS).index(ml.PRODUCTION_MODEL_KEY),
        format_func=lambda k: MODEL_LABELS[k],
    )
    rankings = model_rankings(model_key)
    if rankings is None or rankings.empty:
        missing(ml.MODELS[model_key]["rankings"])
        return

    sectors = sorted(rankings["sector"].dropna().unique())
    chosen = st.multiselect("Filter sectors", sectors, default=sectors)
    vmax = float(rankings["volatility_60d"].max())
    vol_cap = st.slider("Max 60-day volatility", 0.0, round(vmax, 2), round(vmax, 2), step=0.05)
    view = rankings[rankings["sector"].isin(chosen) & (rankings["volatility_60d"] <= vol_cap)]

    st.caption(f"{len(view)} of {len(rankings)} stocks shown (ranked by predicted 63-day return).")
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.plotly_chart(mp.plot_rankings_scatter(view), use_container_width=True)
    st.caption("Dotted lines mark the conservative / balanced / aggressive volatility caps (0.35 / 0.50 / 0.80).")


def _profile_block(profile, recs, sectors_df):
    holdings = recs[recs["profile"] == profile].sort_values("rank")
    st.dataframe(
        holdings[["rank", "ticker", "sector", "industry", "weight",
                  "predicted_63d_return", "volatility_60d"]],
        use_container_width=True,
        hide_index=True,
    )
    if sectors_df is not None:
        st.plotly_chart(mp.plot_sector_allocation(sectors_df, profile), use_container_width=True)
    return holdings


def page_recommender():
    st.title("Portfolio Recommender")
    export_banner()
    recs = portfolio_recs()
    summary = portfolio_summary()
    sectors_df = portfolio_sectors()
    if recs is None or summary is None:
        missing("portfolio_recommendations.csv / portfolio_summary.csv")
        return

    st.subheader("Tell us about you")
    col1, col2, col3 = st.columns(3)
    horizon = col1.select_slider("Investment horizon", ["Short", "Medium", "Long"], value="Medium")
    loss = col2.radio(
        "If your portfolio dropped 20% in a month you would…",
        ["Sell to stop losses", "Hold and wait", "Buy more"],
        index=1,
    )
    comfort = col3.radio("Comfort with price swings", ["Low", "Medium", "High"], index=1)

    score = (
        {"Short": 0, "Medium": 1, "Long": 2}[horizon]
        + {"Sell to stop losses": 0, "Hold and wait": 1, "Buy more": 2}[loss]
        + {"Low": 0, "Medium": 1, "High": 2}[comfort]
    )
    suggested = "conservative" if score <= 1 else ("balanced" if score <= 4 else "aggressive")

    profile = st.selectbox(
        "Recommended profile (override if you like)",
        list(ml.PROFILES.keys()),
        index=list(ml.PROFILES.keys()).index(suggested),
        format_func=str.title,
    )
    cap = ml.PROFILES[profile]["max_volatility_60d"]
    st.success(f"**You are: {profile.title()}** — {ml.PROFILES[profile]['description']}")
    st.caption(f"Volatility cap applied: ≤ {cap} (60-day). Portfolio is precomputed — not re-selected here.")

    prow = summary[summary["profile"] == profile]
    if not prow.empty:
        prow = prow.iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Expected 63-day return", pct(prow["expected_63d_return_weighted"]))
        m2.metric("Avg 60-day volatility", pct(prow["avg_volatility_60d_weighted"]))
        m3.metric("Sectors / cap relaxed", f"{int(prow['sectors'])} / {bool(prow['volatility_cap_relaxed'])}")

    holdings = _profile_block(profile, recs, sectors_df)
    st.plotly_chart(mp.plot_portfolio_risk_return(summary), use_container_width=True)

    with st.expander("Diversification check — holding correlation"):
        wide = root_wide()
        cols = [t for t in holdings["ticker"] if t in wide.columns]
        if len(cols) >= 2:
            returns = wide[cols].pct_change().dropna()
            st.plotly_chart(mp.plot_portfolio_correlation(returns), use_container_width=True)
        else:
            st.info("Not enough holdings present in the current root price matrix to compute correlation.")


def page_portfolios():
    st.title("Portfolios")
    export_banner()
    summary = portfolio_summary()
    recs = portfolio_recs()
    sectors_df = portfolio_sectors()
    if summary is None or recs is None:
        missing("portfolio_*.csv")
        return

    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.plotly_chart(mp.plot_portfolio_risk_return(summary), use_container_width=True)

    tabs = st.tabs([p.title() for p in ml.PROFILES])
    for tab, profile in zip(tabs, ml.PROFILES):
        with tab:
            _profile_block(profile, recs, sectors_df)


def page_archive():
    st.title("Archive")
    st.caption("Historical artifacts and the data-source comparison, kept out of the main demo flow.")

    st.subheader("Data source comparison — yfinance vs Alpaca (IEX)")
    st.markdown(
        "Static audit (from the earlier Alpaca S&P 500 snapshot):\n"
        "- Comparable (ticker, date) pairs: **1,220,352**\n"
        "- Median absolute relative difference on raw close: **0.000%**\n"
        "- p99: **95%** · max: **400.349%** (split / listing artifacts, not corruption)\n"
        "- Agreement on overlapping pairs ≈ **99.5%**"
    )
    st.markdown(
        "Full interactive comparison lives in the archived HTML reports:\n"
        "- `Archive/experiments/dashboard.html`\n"
        "- `Archive/experiments/data provider choose.html`\n\n"
        "The yfinance dataset (543 tickers incl. DAX 40) is archived under "
        "`Archive/experiments/yfinance/` — the live app uses Alpaca S&P 500 only."
    )

    st.subheader("Reference documents")
    st.markdown(
        "Course deliverables and the Step-1 data audit live under `Formalities/` "
        "(`DATA_AUDIT.md`, `Timeline.md`, `Rendering1/`). The active model run and its "
        "model reports are under `Archive/runs/" + ACTIVE_RUN + "/`."
    )


def page_configurables():
    import pandas as pd

    st.title("Configurables")
    st.caption(
        "Every tunable knob in the data-processing & modeling pipeline, with its current "
        "value and where it is defined. The app is read-only — change these in the source / "
        "`config/paths.yaml`, then rebuild with `make build-db` / `make pipeline`."
    )

    caps = ml.PROFILES
    rows = [
        # Run & paths
        ("Run & paths", "active_run", ACTIVE_RUN, "config/paths.yaml", "Which Archive/runs/<date> feeds the app (data + models)"),
        ("Run & paths", "endproduct_root", "../endproduct", "config/paths.yaml", "Symlink root the code reads data/models/figures from"),
        ("Run & paths", "DB_PATH", "<run>/data/liora.duckdb", "src/db.py", "The single analytical database (one per run)"),
        # Data fetch
        ("Data fetch", "--years", "10", "fetch_data.py", "History window pulled from Alpaca"),
        ("Data fetch", "--batch-size", "1", "fetch_data.py", "Symbols per Alpaca bars request"),
        ("Data fetch", "--limit", "None", "fetch_data.py", "Cap number of tickers (smoke test)"),
        ("Data fetch", "--feed", "iex", "fetch_data.py", "Alpaca data feed (free IEX)"),
        ("Data fetch", "timeframe", "1Day", "fetch_data.py", "Bar granularity (daily OHLCV)"),
        ("Data fetch", "adjustment", "raw + all", "fetch_data.py", "Fetch raw and split/dividend-adjusted close"),
        ("Data fetch", "REQUEST_PAUSE_SEC", "0.35", "fetch_data.py", "Pause between requests (rate-limit)"),
        ("Data fetch", "universe", "S&P 500 (Wikipedia)", "fetch_data.py", "Constituent list source"),
        ("Data fetch", "--export-csv", "False", "fetch_data.py", "Also write legacy CSV artifacts"),
        # Feature engineering (SQL)
        ("Features (SQL)", "ret_* windows", "5 / 20 / 60", "src/features.sql", "Momentum lookbacks (trading days)"),
        ("Features (SQL)", "mean_return windows", "20 / 60", "src/features.sql", "Rolling mean-return lookbacks"),
        ("Features (SQL)", "volatility windows", "20 / 60", "src/features.sql", "Rolling volatility lookbacks"),
        ("Features (SQL)", "avg_volume window", "20", "src/features.sql", "Liquidity lookback (then ln(1+x))"),
        ("Features (SQL)", "drawdown window", "252 (min 60)", "src/features.sql", "1-year peak lookback for drawdown"),
        ("Features (SQL)", "annualization", "×252 / ×√252", "src/features.sql", "Daily→annual scaling (mean / vol)"),
        ("Features (SQL)", "std", "sample (ddof=1)", "src/features.sql", "STDDEV_SAMP — matches legacy pandas"),
        # Target / label
        ("Target (label)", "TARGET_HORIZON_DAYS", "63", "features.sql / train_xgb_optuna.py", "Forward horizon for the label"),
        ("Target (label)", "target_63d_return", "LEAD(adj_close,63)/adj_close − 1", "src/features.sql", "Y = forward 63-day return (regression, NOT triple-barrier)"),
        # Model inputs
        ("Model inputs", "NUMERIC_FEATURES", "9 columns", "train_xgb_optuna.py", "ret_5/20/60d · mean_return_20/60d · volatility_20/60d · log_avg_volume_20d · drawdown_252d"),
        ("Model inputs", "CAT_FEATURE", "sector", "train_xgb_optuna.py", "Native XGBoost category (not one-hot)"),
        ("Model inputs", "excluded", "history_days, industry", "train_xgb_optuna.py", "history_days = leak; industry = display only"),
        # Train / test split
        ("Train/test split", "TEST_START_DATE", "2025-01-01", "train_xgb_optuna.py", "Test = dates ≥ this; train = before"),
        ("Train/test split", "VAL_START_DATE", "2024-07-01", "train_xgb_optuna.py", "Last ~6 mo of train = Optuna validation"),
        ("Train/test split", "RANDOM_SEED", "42", "train_xgb_optuna.py", "Seed for XGBoost + Optuna sampler"),
        # Model + Optuna
        ("Model / Optuna", "production model", ml.PRODUCTION_MODEL_KEY, "train_xgb_optuna.py", "Single live training pipeline (XGBoost+Optuna)"),
        ("Model / Optuna", "objective", "reg:squarederror", "train_xgb_optuna.py", "Regression on forward return"),
        ("Model / Optuna", "tree_method", "hist", "train_xgb_optuna.py", "XGBoost histogram method"),
        ("Model / Optuna", "--trials", "30", "Makefile / train_xgb_optuna.py", "Optuna trials"),
        ("Model / Optuna", "tuning metric", "validation Spearman (maximize)", "train_xgb_optuna.py", "What Optuna optimizes"),
        ("Model / Optuna", "n_estimators", "200–700 step 50", "train_xgb_optuna.py", "Search range"),
        ("Model / Optuna", "max_depth", "3–8", "train_xgb_optuna.py", "Search range"),
        ("Model / Optuna", "learning_rate", "0.01–0.3 (log)", "train_xgb_optuna.py", "Search range"),
        ("Model / Optuna", "min_child_weight", "5–50", "train_xgb_optuna.py", "Search range"),
        ("Model / Optuna", "subsample", "0.6–1.0", "train_xgb_optuna.py", "Search range"),
        ("Model / Optuna", "colsample_bytree", "0.6–1.0", "train_xgb_optuna.py", "Search range"),
        ("Model / Optuna", "reg_lambda", "0.0–10.0", "train_xgb_optuna.py", "L2 regularization search range"),
        ("Model / Optuna", "reg_alpha", "0.0–1.0", "train_xgb_optuna.py", "L1 regularization search range"),
        # Evaluation
        ("Evaluation", "top-k", "5 & 10", "train_xgb_optuna.py", "Top-k picks for realized-return metric"),
        ("Evaluation", "metrics", "MAE · RMSE · Spearman · top5", "train_xgb_optuna.py", "Test-split metrics tracked"),
        # Walk-forward
        ("Walk-forward", "init train", "504 days", "walk_forward.sh", "Initial expanding-window train size"),
        ("Walk-forward", "test window", "63 days", "walk_forward.sh", "Out-of-sample window per fold"),
        ("Walk-forward", "step", "63 days", "walk_forward.sh", "Roll-forward step"),
        ("Walk-forward", "params", "fixed best_params.json", "walk_forward.sh", "No per-fold retune (fast, leak-free)"),
        # Portfolios
        ("Portfolios", "PORTFOLIO_SIZE", str(ml.PORTFOLIO_SIZE), "model_loader.py / build_portfolios.sql", "Stocks per portfolio"),
        ("Portfolios", "MAX_SECTOR_WEIGHT", f"{ml.MAX_SECTOR_WEIGHT:.0%}", "model_loader.py / build_portfolios.sql", "→ max floor(10×0.30)=3 per sector"),
        ("Portfolios", "MAX_STOCK_WEIGHT", f"{ml.MAX_STOCK_WEIGHT:.0%}", "model_loader.py", "Per-stock cap (equal weight 1/N used)"),
        ("Portfolios", "vol cap · conservative", str(caps["conservative"]["max_volatility_60d"]), "model_loader.py / build_portfolios.sql", "60-day volatility ceiling"),
        ("Portfolios", "vol cap · balanced", str(caps["balanced"]["max_volatility_60d"]), "model_loader.py / build_portfolios.sql", "60-day volatility ceiling"),
        ("Portfolios", "vol cap · aggressive", str(caps["aggressive"]["max_volatility_60d"]), "model_loader.py / build_portfolios.sql", "60-day volatility ceiling"),
        ("Portfolios", "cap relax rule", "<10 eligible → relax", "build_portfolios.sql", "Relax vol cap if too few names clear it"),
        # App / display
        ("App / display", "APP_PORT", "8501", "Makefile", "Streamlit port"),
        ("App / display", "feature-importance top_n", "12", "src/model_plots.py", "Bars shown in importance charts"),
        ("App / display", "pred-vs-actual bins", "60", "src/model_plots.py", "Density-heatmap resolution"),
    ]
    df = pd.DataFrame(rows, columns=["Stage", "Parameter", "Value", "Defined in", "Controls"])

    stages = list(dict.fromkeys(df["Stage"]))
    chosen = st.multiselect("Filter by stage", stages, default=stages)
    view = df[df["Stage"].isin(chosen)]
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.caption(f"{len(view)} configurables across {view['Stage'].nunique()} stages.")


PAGES = {
    "Overview": page_overview,
    "Data Audit": page_data_audit,
    "EDA": page_eda,
    "Model Leaderboard": page_model_leaderboard,
    "Model Explorer": page_model_explorer,
    "Walk-Forward": page_walk_forward,
    "Rankings": page_rankings,
    "Recommender": page_recommender,
    "Portfolios": page_portfolios,
    "Configurables": page_configurables,
    "Archive": page_archive,
}

st.sidebar.title("Navigation")
choice = st.sidebar.radio("Page", list(PAGES.keys()))
st.sidebar.caption("Read-only demo · no training at runtime")
PAGES[choice]()
