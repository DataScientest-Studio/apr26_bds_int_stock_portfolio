#!/usr/bin/env python3
"""make test-app: correctness gates + smoke of every page of the unified Streamlit app.

Part 1 — pure-pandas gates on the preset-package rule (determinism, sector cap, volatility cap,
relax path, pre-OOS coverage) for BOTH sealed methods.
Part 2 — streamlit.testing.v1.AppTest renders each page and asserts no exception; the simulator
is driven through start -> pick -> preset apply; the recommender must produce a 10-name package
under the defaults with the sector cap respected.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import pandas as pd  # noqa: E402

FAILS = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def gate_package_rule():
    print("Part 1 — package rule gates")
    import sqlite3

    from package_builder import build_package

    pre = pd.read_csv(ROOT / "app" / "data" / "preoos_inputs.csv")
    check("pre-OOS inputs fail-closed", (pre["asof_date"] <= "2023-12-29").all(),
          f"max asof {pre['asof_date'].max()}")
    meta = pd.read_csv(ROOT / "app" / "data" / "tickers.csv")[["ticker", "sector", "industry"]]

    for name, db in [("XGBoost", ROOT / "xgb" / "data" / "oos_metrics.db"),
                     ("LSTM", ROOT / "lstm" / "oos_metrics.db")]:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        df = pd.read_sql_query("select ticker, cv_auc_pr from oos_metrics", con)
        con.close()
        pool = (df.merge(pre[["ticker", "volatility_60d", "ret_60d"]], on="ticker", how="inner")
                  .merge(meta, on="ticker", how="left"))
        pool["sector"] = pool["sector"].fillna("Unknown")
        check(f"{name}: pool covers store", len(pool) >= 0.95 * len(df),
              f"{len(pool)}/{len(df)} rows after pre-OOS merge")

        args = dict(portfolio_size=10, max_volatility_60d=0.50, max_sector_weight=0.30,
                    excluded_sectors=[], min_recent_return=-0.80,
                    ranking_objective="Risk-adjusted return")
        s1, _, r1 = build_package(pool, **args)
        s2, _, _ = build_package(pool, **args)
        check(f"{name}: deterministic", list(s1["ticker"]) == list(s2["ticker"]))
        check(f"{name}: size 10", len(s1) == 10, ", ".join(s1["ticker"]))
        check(f"{name}: sector cap <=3", int(s1["sector"].value_counts().max()) <= 3)
        check(f"{name}: vol cap respected (not relaxed)",
              (not r1) and (s1["volatility_60d"] <= 0.50).all())
        # artificially strict cap must trigger the relax path (still sector-capped)
        s3, _, r3 = build_package(pool, **{**args, "max_volatility_60d": 0.05})
        check(f"{name}: relax path triggers", r3 and len(s3) == 10
              and int(s3["sector"].value_counts().max()) <= 3)
        # excluded sector never appears
        s4, _, _ = build_package(pool, **{**args, "excluded_sectors": ["Information Technology"]})
        check(f"{name}: sector exclusion", not (s4["sector"] == "Information Technology").any())

    # XGB HODL feed is sealed for every asset
    import json
    feed = json.loads((ROOT / "xgb" / "plan" / "data" / "dashboard.json").read_text())["assets"]
    n_hodl = sum(1 for a in feed if a.get("hodl_return_pct") is not None)
    bad = [a["ticker"] for a in feed if a.get("hodl_return_pct") is not None
           and a["beats_hodl"] != (a["return_pct"] > a["hodl_return_pct"])]
    check("XGB HODL sealed 498/498", n_hodl == len(feed) == 498, f"{n_hodl}/{len(feed)}")
    check("XGB beats_hodl consistent", not bad, ", ".join(bad[:5]))


def _page_script(module_name: str, app_dir: str) -> None:
    """Self-contained page runner for AppTest.from_function (which executes the function's SOURCE
    in a fresh namespace — module globals don't exist there, so everything imports inside)."""
    import sys
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    import importlib
    importlib.import_module(module_name).render()


def make_apptest(module_name: str):
    from streamlit.testing.v1 import AppTest
    return AppTest.from_function(
        _page_script, kwargs={"module_name": module_name, "app_dir": str(ROOT / "app")})


def gate_simulator_flow():
    at = make_apptest("page_simulator")
    at.run(timeout=120)
    start = [b for b in at.button if b.label == "Start"]
    check("simulator: Start button", bool(start))
    if not start:
        return
    start[0].click()
    at.run(timeout=120)
    check("simulator: pick stage renders", not at.exception and at.session_state["stage"] == "pick")
    # choose the Balanced preset via its selectbox, then apply
    sel = [s for s in at.selectbox if s.label == "Preset"]
    check("simulator: preset selectbox", bool(sel))
    if sel:
        sel[0].select("Balanced")
        at.run(timeout=120)
        apply_btn = [b for b in at.button if b.label == "Apply preset"]
        check("simulator: apply button", bool(apply_btn))
        if apply_btn:
            apply_btn[0].click()
            at.run(timeout=120)
            basket = at.session_state["basket"]
            check("simulator: preset pre-selects 10", len(basket) == 10, ", ".join(sorted(basket)))
            calc = [b for b in at.button if b.label == "Calculate basket"]
            if calc:
                calc[0].click()
                at.run(timeout=120)      # calc stage sleeps 1.5s then reruns into result
                check("simulator: result renders", not at.exception
                      and at.session_state["stage"] == "result")
                # HODL benchmark must be present for the default method (XGBoost) now
                texts = " ".join(str(m.value) for m in at.metric)
                check("simulator: HODL metric shown", "Buy & hold" in
                      " ".join(m.label for m in at.metric), texts)


def main():
    gate_package_rule()
    print()
    print("Part 2 — page smoke (AppTest)")
    from streamlit.testing.v1 import AppTest  # noqa: F401 — fail early if missing

    def run_page(name, module_name, timeout=120):
        at = make_apptest(module_name)
        at.run(timeout=timeout)
        check(f"page renders: {name}", not at.exception,
              str(at.exception[0].value) if at.exception else "")
        return at

    run_page("Project Report", "page_report")
    run_page("Data Explorer", "page_explorer", timeout=300)
    run_page("Risk Profile", "page_risk")
    run_page("Methodology & Integrity", "page_methodology")
    run_page("Pipeline Blueprint", "page_blueprint")
    # Its own AppTest instance on purpose: the vendored study's simulator shares session keys
    # (and a "Calculate basket" button label) with page_simulator, so the two must never render
    # in one run. The page namespaces those keys at runtime; this keeps the gate honest anyway.
    run_page("Per Ticker ML-Model", "page_per_ticker_ml", timeout=300)
    at = run_page("Recommender (Track B)", "page_recommender")
    if not at.exception:
        rec = next((d.value for d in at.dataframe
                    if "predicted_63d_return" in getattr(d.value, "columns", [])), None)
        check("recommender: 10-name package", rec is not None and len(rec) == 10,
              f"{0 if rec is None else len(rec)} rows")
        if rec is not None:
            check("recommender: sector cap <=3", int(rec["sector"].value_counts().max()) <= 3)
    gate_simulator_flow()

    print()
    if FAILS:
        print(f"FAILED: {len(FAILS)} gate(s): {FAILS}")
        raise SystemExit(1)
    print("ALL GATES PASS")


if __name__ == "__main__":
    main()
