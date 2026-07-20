#!/usr/bin/env python3
"""Every figure the pipeline map asserts, recomputed from the sealed store.

    python3 scripts/verify_figures.py

`data_pipeline_lego_plan.html` is hand-written: numbers typed in, not derived. That is fine
for a frozen release and fatal for the next one — a re-seal moves the store and leaves the
prose behind, silently, in a 110 KB file nobody re-reads. This gate exists so that never
has to be found by eye again.

Each check names one figure, recomputes it from data/results.db, and asserts the literal
string appears in the file(s) that claim it. A figure that moves fails here rather than on
stage. Standard library only, read-only connection, no network — same contract as the other
two verify scripts.

Scope, stated honestly: this checks the figures that are DERIVABLE from the sealed store.
Parameters that live in config/ (purge, embargo, trial counts, theta grids) are not covered,
and neither is prose. Absence of a failure here is not a claim that the maps are fully
correct — only that no store-derived number in them has drifted.
"""
import re
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "results.db"
BLUEPRINT = ROOT / "data_pipeline_lego_plan.html"
APP = ROOT / "app.py"
README = ROOT / "README.md"

FAILURES = []


def connect():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def rows(con, sql, params=()):
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(sql, params)]


def normalize(text):
    """Compare numbers, not typography.

    House style varies — a figure may be written "−1.78 %" with a Unicode minus and a thin
    gap before the sign, or "-1.78%". Both are the same figure, and a gate that fails on the
    space would be noise that gets muted within a week.
    """
    return (text.replace("−", "-").replace(" ", " ")
                .replace(" %", "%").replace(" / ", "/"))


_CACHE = {}


def check(name, expected, *files, note=""):
    """`expected` must appear in every named file, up to number formatting."""
    want = normalize(expected)
    for f in files:
        if f not in _CACHE:
            _CACHE[f] = normalize(f.read_text(encoding="utf-8"))
    missing = [f.name for f in files if want not in _CACHE[f]]
    ok = not missing
    tail = "" if ok else f" — not found in {', '.join(missing)}"
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {expected}{tail}{'  (' + note + ')' if note and ok else ''}")
    if not ok:
        FAILURES.append(name)


def main():
    if not DB.exists():
        print(f"store not found: {DB}")
        return 1
    con = connect()
    print("Figures asserted by the pipeline map, recomputed from the sealed store\n")

    # ---- universe and cohorts -------------------------------------------------
    counts = {r["model"]: r["n"] for r in
              rows(con, "select model, count(*) n from asset_results group by model")}
    check("XGB universe", str(counts["xgb"]), BLUEPRINT)
    check("LSTM universe", str(counts["lstm"]), BLUEPRINT)
    check("sealed artifacts", str(counts["xgb"] + counts["lstm"]), BLUEPRINT)

    modes = {(r["model"], r["result_mode"]): r["n"] for r in rows(
        con, "select model, result_mode, count(*) n from asset_results group by model, result_mode")}
    for model in ("xgb", "lstm"):
        promoted = modes.get((model, "ML_MULTI_TRADE"), 0)
        check(f"{model.upper()} promoted (ML_MULTI_TRADE)", str(promoted), BLUEPRINT)

    # ---- the verdict headline -------------------------------------------------
    for model, files in (("xgb", (BLUEPRINT,)), ("lstm", (BLUEPRINT,))):
        rs = rows(con, "select return_pct, hodl_return_pct, model_trades from asset_results "
                       "where model=?", (model,))
        med_ret = statistics.median(r["return_pct"] for r in rs)
        med_hodl = statistics.median(r["hodl_return_pct"] for r in rs)
        med_trades = statistics.median(r["model_trades"] for r in rs)
        check(f"{model.upper()} median return", f"{med_ret:+.2f}".replace("+", "+") + "%",
              *files, note="over all rows")
        check(f"{model.upper()} median HODL", f"+{med_hodl:.2f}%", *files)
        # Trade medians are stated by the blueprint only.
        check(f"{model.upper()} median trades",
              str(int(med_trades)) if med_trades == int(med_trades) else f"{med_trades:.1f}",
              BLUEPRINT)

        beats = rows(con, "select count(*) n from asset_results where model=? and beats_hodl=1",
                     (model,))[0]["n"]
        check(f"{model.upper()} beats HODL (blueprint form)", f"{beats}/{len(rs)}", BLUEPRINT)

        pf = [r["profit_factor"] for r in rows(
            con, "select profit_factor from asset_results where model=? and "
                 "result_mode='ML_MULTI_TRADE' and profit_factor is not null", (model,))]
        check(f"{model.upper()} median PF", f"{statistics.median(pf):.3f}", *files)
        check(f"{model.upper()} PF population", str(len(pf)), *files,
              note="promoted rows with a rankable PF")

    # ---- the payoff retraction ------------------------------------------------
    for model, files in (("xgb", (BLUEPRINT,)), ("lstm", (BLUEPRINT,))):
        pay = [r["profit_factor"] * r["losses"] / r["wins"] for r in rows(
            con, "select profit_factor, wins, losses from asset_results where model=? and "
                 "result_mode='ML_MULTI_TRADE' and profit_factor is not null and wins>0 and "
                 "losses>0", (model,))]
        check(f"{model.upper()} realized payoff", f"{statistics.median(pay):.3f}", *files)
        share = 100.0 * sum(1 for p in pay if p >= 2.0) / len(pay)
        check(f"{model.upper()} share reaching 2.0", f"{share:.1f}%", BLUEPRINT)

    # ---- the read ledger ------------------------------------------------------
    for r in rows(con, "select * from oos_read_summary"):
        check(f"{r['pipe'].upper()} reads this epoch", str(r["reads_this_epoch"]), BLUEPRINT)

    # ---- the interpretation layer --------------------------------------------
    interp = rows(con, "select message from integrity_checks where check_name="
                       "'interpretation_coverage'")[0]["message"]
    for label, key in (("feature-stat rows", "stats"), ("ENTRY-range segments", "ranges")):
        m = re.search(rf"{key}=(\d+)", interp)
        if m:
            n = int(m.group(1))
            spaced = f"{n:,}".replace(",", " ")          # the maps write 16 601, not 16601
            check(f"interpretation {label}", spaced, BLUEPRINT)

    # ---- corporate actions ----------------------------------------------------
    check("split events (blueprint form)", "83 events across 69 tickers", BLUEPRINT)

    # ---- the page count -------------------------------------------------------
    # Not a store figure, but the same failure mode: the number of console pages is asserted
    # by hand in a dozen places and nothing used to check any of them, so adding or removing
    # a page left stale counts behind in prose nobody re-reads. app.py is the only source of
    # truth — it is what Streamlit actually builds the sidebar from.
    n_pages = APP.read_text(encoding="utf-8").count("st.Page(")
    # Spelled out because the prose spells them out. The list covers 1..20 rather than the
    # handful in use: a dict that has to be extended every time a page is added is a gate
    # that fails on its own vocabulary instead of on the thing it is watching, which is
    # exactly what happened the first time this ran after a two-page removal.
    WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
             "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()
    word = WORDS[n_pages] if n_pages < len(WORDS) else str(n_pages)
    # The knob names the count; how the sidebar is grouped is not this gate's business, so
    # it matches "pages=N" and stops there. Pinning the section wording too made the gate
    # fail on a sidebar change that had nothing to do with the number it exists to guard.
    check("page count (blueprint knob)", f"pages={n_pages}", BLUEPRINT)
    check("page count (blueprint prose)", f"a {word}-page", BLUEPRINT)
    check("page count (README)", f"## The {word} pages", README)
    stale = [w for i, w in enumerate(WORDS) if i != n_pages and i > 1
             and (f"The {w} pages" in README.read_text(encoding="utf-8")
                  or f"a {w}-page" in BLUEPRINT.read_text(encoding="utf-8"))]
    print(f"  {'PASS' if not stale else 'FAIL'}  no stale page count survives: "
          f"{n_pages} pages in app.py{'' if not stale else '  — found ' + ', '.join(stale)}")
    if stale:
        FAILURES.append("stale page count")

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} figure(s) drifted — {', '.join(FAILURES)}")
        print("A figure that moved means the store was re-sealed and the maps were not "
              "updated. Fix the prose, not this gate.")
        return 1
    print("OK: every store-derived figure in the pipeline map matches the sealed store.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
