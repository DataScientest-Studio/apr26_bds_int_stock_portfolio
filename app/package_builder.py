"""Preset-package rules: the parent project's portfolio-construction logic, ported for both tracks.

Two rule variants share the same skeleton (filters -> objective score -> greedy pick under a
per-sector cap -> equal weight, relax-only-the-volatility-cap-if-underfilled):

* ``apply_recommendation_preferences`` — the Track-B original, VERBATIM from
  ``mac-2026-06-09-full-6y/app.py``: ranks by the Random-Forest ``predicted_63d_return``.
  Used ONLY on the Recommender page, where results are model predictions (exploratory tier).

* ``build_package`` — the Track-A adaptation for the Basket Simulator. The sealed OOS rows it
  pre-selects are REAL one-shot results, so every input must be knowable before the OOS window:
    - ranking score  = ``cv_auc_pr``   (Train-CV metric sealed in each row — decided pre-OOS)
    - volatility / recent return       = as of <= 2023-12-29 (app/data/preoos_inputs.csv)
    - sector                           = static GICS metadata (app/data/tickers.csv)
  The parent's ``predicted_63d_return`` rankings are dated 2026-06-08 — the END of the OOS
  window — and are therefore look-ahead for this purpose; they are never used here.
  The three objectives become unit-free z-score analogues (documented in-app).

``risk_answers_to_recommendation_defaults`` (the 9-question form -> control defaults mapping)
is ported 1:1 and shared by both pages.
"""
import math

import pandas as pd

PROFILE_CONFIG = {
    "Conservative": {
        "max_volatility_60d": 0.35,
        "description": "Lower volatility first, with a stricter cap on jumpy stocks.",
    },
    "Balanced": {
        "max_volatility_60d": 0.50,
        "description": "Middle risk level with room for moderate volatility.",
    },
    "Aggressive": {
        "max_volatility_60d": 0.80,
        "description": "Higher risk tolerance when the model score is strong.",
    },
    "Custom": {
        "max_volatility_60d": 0.50,
        "description": "User-defined risk and diversification settings.",
    },
}

OBJECTIVES = ["Highest expected return", "Risk-adjusted return", "Smoother ride"]


def risk_answers_to_recommendation_defaults(risk_answers: dict | None) -> dict:
    """Translate the risk questionnaire into recommender control defaults (ported 1:1)."""
    defaults = {
        "profile": "Balanced",
        "max_volatility_60d": 0.50,
        "portfolio_size": 10,
        "ranking_objective": "Highest expected return",
        "max_sector_weight_pct": 30,
        "excluded_sectors": [],
        "min_predicted_return_pct": 0,
        "min_recent_return_pct": -80,
    }
    if not risk_answers:
        return defaults

    score = 0
    score += {"Beginner": -1, "Some experience": 0, "Experienced": 1}.get(
        risk_answers.get("experience"), 0
    )
    score += {
        "Less than 1 week": -1,
        "1-4 weeks": 0,
        "1-12 months": 1,
        "1+ year": 1,
    }.get(risk_answers.get("horizon"), 0)
    score += {"5%": -2, "10%": -1, "20%": 1, "30% or more": 2}.get(
        risk_answers.get("loss_tolerance"), 0
    )
    score += {"Sell everything": -2, "Sell part of it": -1, "Hold": 0, "Buy more": 1}.get(
        risk_answers.get("drawdown_reaction"), 0
    )
    score += {
        "Minimize losses, even if it means missing some gains": -2,
        "Maximize potential returns, even if it means larger swings": 2,
        "Balance steady, moderate gains against moderate risk": 0,
    }.get(risk_answers.get("goal"), 0)

    if score <= -3:
        defaults["profile"] = "Conservative"
        defaults["ranking_objective"] = "Smoother ride"
        defaults["min_recent_return_pct"] = -10
    elif score >= 3:
        defaults["profile"] = "Aggressive"
        defaults["ranking_objective"] = "Highest expected return"
        defaults["min_predicted_return_pct"] = 2
    else:
        defaults["profile"] = "Balanced"
        defaults["ranking_objective"] = "Risk-adjusted return"
        defaults["min_recent_return_pct"] = -30

    if risk_answers.get("goal") == "Minimize losses, even if it means missing some gains":
        defaults["ranking_objective"] = "Smoother ride"
    elif risk_answers.get("goal") == "Maximize potential returns, even if it means larger swings":
        defaults["ranking_objective"] = "Highest expected return"
    elif risk_answers.get("goal") == "Balance steady, moderate gains against moderate risk":
        defaults["ranking_objective"] = "Risk-adjusted return"

    defaults["portfolio_size"] = {
        "Few (1-3)": 3,
        "Moderate (4-7)": 7,
        "Fully diversified (8-10)": 10,
    }.get(risk_answers.get("position_count"), defaults["portfolio_size"])
    defaults["max_sector_weight_pct"] = {
        "Few (1-3)": 60,
        "Moderate (4-7)": 40,
        "Fully diversified (8-10)": 30,
    }.get(risk_answers.get("position_count"), defaults["max_sector_weight_pct"])
    defaults["excluded_sectors"] = risk_answers.get("sectors_avoid") or []
    defaults["max_volatility_60d"] = PROFILE_CONFIG[defaults["profile"]]["max_volatility_60d"]
    return defaults


def _greedy_sector_capped(candidate_pool: pd.DataFrame, portfolio_size: int,
                          max_sector_weight: float) -> pd.DataFrame:
    """Greedy top-down pick under the per-sector cap (the parent's exact loop)."""
    max_sector_count = max(1, math.floor(portfolio_size * max_sector_weight))
    selected_rows = []
    sector_counts: dict[str, int] = {}
    for _, row in candidate_pool.iterrows():
        sector = row["sector"]
        if sector_counts.get(sector, 0) >= max_sector_count:
            continue
        selected_rows.append(row)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        if len(selected_rows) == portfolio_size:
            break
    return pd.DataFrame(selected_rows)


def _finalize(selected: pd.DataFrame) -> pd.DataFrame:
    selected = selected.copy()
    selected.insert(0, "rank", range(1, len(selected) + 1))
    selected["weight"] = 1 / len(selected)
    selected["sector_weight"] = selected.groupby("sector")["weight"].transform("sum")
    return selected


def apply_recommendation_preferences(
    rankings: pd.DataFrame,
    portfolio_size: int,
    max_volatility_60d: float,
    max_sector_weight: float,
    excluded_sectors: list[str],
    min_predicted_return: float,
    min_recent_return: float,
    ranking_objective: str,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Track-B original (verbatim port): rule over the RF predicted-return rankings."""
    filtered = rankings.copy()
    filtered = filtered[~filtered["sector"].isin(excluded_sectors)]
    filtered = filtered[filtered["predicted_63d_return"] >= min_predicted_return]
    filtered = filtered[filtered["ret_60d"] >= min_recent_return]

    strict = filtered[filtered["volatility_60d"] <= max_volatility_60d].copy()
    relaxed = False
    candidate_pool = strict

    if len(candidate_pool) < portfolio_size:
        candidate_pool = filtered.copy()
        relaxed = True

    if ranking_objective == "Risk-adjusted return":
        candidate_pool["selection_score"] = (
            candidate_pool["predicted_63d_return"] / candidate_pool["volatility_60d"].clip(lower=0.01)
        )
    elif ranking_objective == "Smoother ride":
        candidate_pool["selection_score"] = (
            candidate_pool["predicted_63d_return"] - 0.35 * candidate_pool["volatility_60d"]
        )
    else:
        candidate_pool["selection_score"] = candidate_pool["predicted_63d_return"]

    candidate_pool = candidate_pool.sort_values(
        ["selection_score", "predicted_63d_return"],
        ascending=False,
    )

    selected = _greedy_sector_capped(candidate_pool, portfolio_size, max_sector_weight)
    if selected.empty:
        return selected, candidate_pool, relaxed
    return _finalize(selected), candidate_pool, relaxed


def build_package(
    pool: pd.DataFrame,
    portfolio_size: int,
    max_volatility_60d: float,
    max_sector_weight: float,
    excluded_sectors: list[str],
    min_recent_return: float,
    ranking_objective: str,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Track-A preset: the same rule skeleton over STRICTLY PRE-OOS inputs.

    ``pool`` columns: ticker, sector, industry, cv_auc_pr, volatility_60d, ret_60d — the merge of
    the selected method's sealed store (Train-CV score only) with the pre-OOS risk table and the
    static sector metadata. The objective scores are unit-free z-score analogues of the parent's
    three objectives (cv_auc_pr replaces the un-usable predicted return). Deterministic: ties break
    on (cv_auc_pr desc, ticker asc).
    """
    filtered = pool.copy()
    filtered = filtered[~filtered["sector"].isin(excluded_sectors)]
    filtered = filtered[filtered["ret_60d"] >= min_recent_return]

    strict = filtered[filtered["volatility_60d"] <= max_volatility_60d].copy()
    relaxed = False
    candidate_pool = strict

    if len(candidate_pool) < portfolio_size:
        candidate_pool = filtered.copy()
        relaxed = True

    def z(s: pd.Series) -> pd.Series:
        sd = s.std(ddof=0)
        return (s - s.mean()) / sd if sd > 0 else s * 0.0

    z_auc = z(candidate_pool["cv_auc_pr"])
    z_vol = z(candidate_pool["volatility_60d"])
    if ranking_objective == "Risk-adjusted return":
        candidate_pool["selection_score"] = z_auc - 0.5 * z_vol
    elif ranking_objective == "Smoother ride":
        candidate_pool["selection_score"] = z_auc - 1.0 * z_vol
    else:                                    # "Highest expected return" -> highest model confidence
        candidate_pool["selection_score"] = z_auc

    candidate_pool = candidate_pool.sort_values(
        ["selection_score", "cv_auc_pr", "ticker"],
        ascending=[False, False, True],
    )

    selected = _greedy_sector_capped(candidate_pool, portfolio_size, max_sector_weight)
    if selected.empty:
        return selected, candidate_pool, relaxed
    return _finalize(selected), candidate_pool, relaxed
