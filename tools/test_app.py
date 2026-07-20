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


def _per_ticker_script(app_dir: str, active: str) -> None:
    """Stand-in for app/app.py around the vendored study: scope sync, then the active page."""
    import sys
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    import page_per_ticker_ml
    page_per_ticker_ml.sync_session_scope(active)
    if active == "per-ticker-ml":
        page_per_ticker_ml.render()
    else:
        import page_simulator
        page_simulator.render()


def _stopping_page_script(caption_first: bool) -> None:
    """Mirror app/app.py's shape around a page that stops: caption, hotkey, then pg.run()."""
    import streamlit as st
    if caption_first:
        st.sidebar.caption("⌨️  **⌘ / Ctrl + B** — hide / show this menu")
    st.write("page body")
    st.stop()                       # what the vendored study does on nearly every render
    if not caption_first:           # unreachable once a stop latches — that is the point
        st.sidebar.caption("⌨️  **⌘ / Ctrl + B** — hide / show this menu")


def gate_app_shell():
    """The two behavioural changes app/app.py carries for the vendored study, which the page
    smoke above cannot see because it calls each page's render() directly.

    1. st.stop() latches ScriptRequestType.STOP for the whole run, so anything drawn after
       pg.run() disappears whenever the active page stops. The sidebar caption and the Ctrl+B
       hotkey therefore have to be drawn BEFORE pg.run() — checked structurally on the real
       file, and behaviourally here with its own negative control.
    2. sync_session_scope() runs on EVERY page now, so it must be inert on a production page
       in a fresh session.
    """
    from streamlit.testing.v1 import AppTest
    print("Part 4 — app shell: stop-survival and scope inertness")

    # Line-based, and only real statements: the surrounding comments mention pg.run() too.
    lines = (ROOT / "app" / "app.py").read_text(encoding="utf-8").splitlines()
    caption_at = next((i for i, ln in enumerate(lines)
                       if ln.lstrip().startswith('st.sidebar.caption("⌨️')), -1)
    run_at = next((i for i, ln in enumerate(lines) if ln.strip() == "pg.run()"), -1)
    check("app.py draws the sidebar caption before pg.run()",
          caption_at != -1 and run_at != -1 and caption_at < run_at,
          f"caption line {caption_at + 1}, pg.run() line {run_at + 1}")

    at = AppTest.from_function(_stopping_page_script, kwargs={"caption_first": True})
    at.run()
    check("caption survives a page that stops", any("Ctrl + B" in c.value for c in at.sidebar.caption))

    neg = AppTest.from_function(_stopping_page_script, kwargs={"caption_first": False})
    neg.run()
    check("negative control: caption after the stop is lost",
          not any("Ctrl + B" in c.value for c in neg.sidebar.caption))

    at = AppTest.from_function(
        _per_ticker_script, kwargs={"app_dir": str(ROOT / "app"), "active": "report"},
        default_timeout=120)
    at.run()
    state = at.session_state.filtered_state
    check("scope sync is inert on a production page in a fresh session",
          state.get("_ptml__owner") == "host"
          and not any(k.startswith("_host__") or k.startswith("_ptml__b") for k in state),
          str({k: v for k, v in state.items() if k.startswith(("_ptml__", "_host__"))}))


def gate_track_b_through_app_shell():
    """Track B's full flow, driven through the app.py path AND after the study has been used.

    gate_simulator_flow() calls page_simulator.render() directly, so it never exercises
    sync_session_scope. This is the sequence a presenter actually performs — play with the
    study, then go back to Track B — and it is the one that would break if key ownership
    handed the wrong basket over.
    """
    from streamlit.testing.v1 import AppTest
    print("Part 5 — Track B still works after the study, through the app shell")

    study = AppTest.from_function(
        _per_ticker_script, kwargs={"app_dir": str(ROOT / "app"), "active": "per-ticker-ml"},
        default_timeout=300)
    study.run()
    if study.exception:
        check("study page renders first", False, str(study.exception[0].value))
        return
    tiles = [b for b in study.button if 1 <= len(b.label) <= 5 and b.label.upper() == b.label]
    if tiles:
        tiles[0].click().run()
    study_basket = set(study.session_state["basket"])
    check("study built a basket", bool(study_basket), str(sorted(study_basket)[:5]))

    at = AppTest.from_function(
        _per_ticker_script, kwargs={"app_dir": str(ROOT / "app"), "active": "simulator"},
        default_timeout=300)
    for key, value in study.session_state.filtered_state.items():
        at.session_state[key] = value
    at.run()
    check("Track B renders after the study", not at.exception,
          str(at.exception[0].value) if at.exception else "")
    if at.exception:
        return

    start = [b for b in at.button if b.label == "Start"]
    check("Track B: Start button", bool(start))
    if not start:
        return
    start[0].click().run()
    check("Track B: pick stage", not at.exception and at.session_state["stage"] == "pick")
    sel = [s for s in at.selectbox if s.label == "Preset"]
    check("Track B: preset selectbox", bool(sel))
    if not sel:
        return
    sel[0].select("Balanced").run()
    apply_btn = [b for b in at.button if b.label == "Apply preset"]
    check("Track B: apply button", bool(apply_btn))
    if not apply_btn:
        return
    apply_btn[0].click().run()
    basket = at.session_state["basket"]
    check("Track B: preset pre-selects 10, not the study's basket",
          len(basket) == 10 and not (set(basket) & study_basket), ", ".join(sorted(basket)))
    calc = [b for b in at.button if b.label == "Calculate basket"]
    if calc:
        calc[0].click().run()
        check("Track B: result renders", not at.exception
              and at.session_state["stage"] == "result",
              str(at.exception[0].value) if at.exception else "")


def gate_per_ticker_callbacks():
    """The study's widgets carry on_change/on_click callbacks, and Streamlit runs those from
    on_script_will_rerun — BEFORE the script body. A swap of the shared session keys scoped to
    this page's render therefore leaves them reading keys that are not there, which crashed the
    Model switch with 'st.session_state has no attribute method_sel'. This drives the widgets
    that fire callbacks, and checks the study's basket still cannot reach page_simulator's keys.
    """
    from streamlit.testing.v1 import AppTest
    print("Part 3 — vendored study: widget callbacks + cross-page key isolation")
    at = AppTest.from_function(
        _per_ticker_script,
        kwargs={"app_dir": str(ROOT / "app"), "active": "per-ticker-ml"}, default_timeout=300)
    at.run()
    check("study page renders", not at.exception,
          str(at.exception[0].value) if at.exception else "")
    if at.exception:
        return

    seg = at.segmented_control
    check("Model switch present", bool(seg))
    if seg:
        other = next((o for o in seg[0].options if o != seg[0].value), None)
        if other:
            seg[0].set_value(other).run()
            check("Model switch callback survives the rerun", not at.exception,
                  str(at.exception[0].value) if at.exception else "")
            check("method followed the switch", at.session_state["method"] == other)

    tiles = [b for b in at.button if 1 <= len(b.label) <= 5 and b.label.upper() == b.label]
    check("ticker tiles present", bool(tiles), f"{len(tiles)} tiles")
    if tiles and not at.exception:
        label = tiles[0].label
        tiles[0].click().run()
        check("ticker tile callback survives the rerun", not at.exception,
              str(at.exception[0].value) if at.exception else "")
        check("tile landed in the study's basket", label in at.session_state["basket"])

    if at.exception:
        return
    study_basket = set(at.session_state["basket"])
    host = AppTest.from_function(
        _per_ticker_script,
        kwargs={"app_dir": str(ROOT / "app"), "active": "simulator"}, default_timeout=300)
    for key, value in at.session_state.filtered_state.items():
        host.session_state[key] = value
    host.run()
    check("Track B simulator renders after the study", not host.exception,
          str(host.exception[0].value) if host.exception else "")
    state = host.session_state.filtered_state
    check("study basket does not leak into Track B",
          not (set(state.get("basket", set())) & study_basket))
    check("study basket parked under _ptml__",
          set(state.get("_ptml__basket", set())) == study_basket)


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
    gate_per_ticker_callbacks()

    print()
    gate_app_shell()

    print()
    gate_track_b_through_app_shell()

    print()
    if FAILS:
        print(f"FAILED: {len(FAILS)} gate(s): {FAILS}")
        raise SystemExit(1)
    print("ALL GATES PASS")


if __name__ == "__main__":
    main()
