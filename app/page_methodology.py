"""Methodology & Integrity: how the sealed tier earns trust, what the exploratory tier lacks, and
the limitations we state instead of hiding. Distilled from docs/PROJECT_STATE.md (Track A) and the
parent project's model reports (Track B).
"""
import streamlit as st

from common import track_a_badge, track_b_badge


def render() -> None:
    st.title("Methodology & Integrity")

    st.subheader("Why 'sealed' means something (Track A)")
    track_a_badge()
    st.markdown(
        """
- **Causal labels.** Entries fill at the *next* bar's open; every feature, gate and barrier input
  uses data ≤ the decision bar's close. The XGBoost pipeline's 1d/1w context joins by close-time
  availability (`merge_asof` backward), so an in-progress coarse bar never leaks into an intraday
  decision.
- **Purged + embargoed walk-forward CV.** Any training event whose Triple-Barrier horizon crosses a
  fold boundary is dropped (purge = horizon), plus an embargo gap after each test fold — the
  standard defense against label overlap (López de Prado).
- **Fold-causal normalization.** Each CV fold's feature statistics come only from rows before its
  embargo boundary; the OOS window uses statistics frozen on the full Train set.
- **Profit-aligned selection.** Optuna maximizes Train out-of-fold trading **log-growth** (the
  Kelly-optimal criterion) — the model is chosen for the objective it will be judged on.
- **One-shot OOS.** The 2024→2026 window is generated and scored **exactly once per asset** at the
  verdict step and never feeds back into any choice — enforced by fail-closed asserts in the HPO,
  the operating-point calibration and the feature search, and independently audited.
- **Costs and sizing.** 1bp commission + 2bp slippage per side; generalized fractional Kelly
  `f = clip(λ·(p−(1−p)/b), 0, cap)` — with `b = 1` this reduces exactly to the classical `λ·(2p−1)`.
- **Reproducibility.** Deterministic per seed: `make verify-xgb` / `make verify-lstm` re-run sample
  assets from the committed data and must reproduce the sealed rows **byte-identically**.
        """
    )

    st.subheader("What the exploratory tier lacks (Track B) — stated, not hidden")
    track_b_badge()
    st.markdown(
        """
- **No purge/embargo:** the 63-trading-day label of the last ~63 training days consumes prices from
  inside the test window — every walk-forward fold leaks at the boundary.
- **Gross returns:** no commissions, slippage, or position sizing.
- **Overlapping horizons:** daily-sampled 63-day labels overlap ~63×, so the pooled Spearman
  overstates the effective sample; fold-count 'wins' (9/13) are not statistically significant at
  conventional levels.
- **Model selection on the test split:** the five-model comparison and the `history_days` diagnosis
  reused one fixed split — there is no untouched holdout on this track.
- **Predictions ≠ backtests:** package 'expected 63-day returns' are model outputs as of the ranking
  date, never realized results.
        """
    )

    st.subheader("Limitations shared by both tracks — and by most retail studies")
    st.markdown(
        """
- **Survivorship bias.** The universe is today's S&P 500 constituents applied backward; delisted
  losers are absent, which flatters every 'universe' benchmark. Acknowledged, not mitigated.
- **Raw prices (Track A store).** Corporate actions are deferred: a split appears as a price cliff.
  The sealed engine trades those raw paths consistently, and the buy-and-hold benchmark uses the
  same raw store, so comparisons are internally consistent — but a split-crossing ticker's absolute
  numbers (e.g. NVDA 2024) are not economically meaningful, and pre-OOS volatility near a split is
  distorted (the package rule keeps its relax-if-underfilled path partly for this reason).
- **IEX-only volumes** (free Alpaca feed): a fraction of consolidated volume; fine for relative
  liquidity ranking, wrong for absolute capacity claims.
- **Sector metadata as of today** applied backward (same class of caveat as survivorship).
- **A strong bull OOS window** (2024→2026): buy-and-hold is a hard benchmark in such regimes; a
  negative verdict here is informative but not a universal claim.
        """
    )

    st.subheader("Rules of engagement this app enforces")
    st.markdown(
        """
1. **Tier badges everywhere.** Any number's evidential standard is visible where the number is.
2. **No cross-tier tables.** Track-A and Track-B results never share a results table or chart.
3. **No look-ahead package selection.** Preset packages for the sealed tier use only pre-OOS inputs
   (Train-CV score, ≤ 2023-12-29 risk stats, static sectors) — verified fail-closed by
   `tools/make_preoos_inputs.py`.
4. **Nothing trains at runtime.** Every page reads committed artifacts; the app is a viewer, not a
   laboratory.
5. **Fixed rules, honestly framed.** The sealed OOS rows were published before the package rule was
   ported, so preset baskets are an *illustration of a rule fixed ex-ante in the parent project* —
   the rule is never tuned against the displayed outcomes.
        """
    )
    st.caption("Deeper dives: docs/UNIFIED_APP.md (this app), docs/PROJECT_STATE.md (Track-A "
               "handoff, audits, re-seal history), xgb/README.md and lstm/README.md (research "
               "integrity sections).")
