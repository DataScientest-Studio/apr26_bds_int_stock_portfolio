"""Build constrained portfolios from model rankings.

Uses the current best model output:
    models/random_forest_no_history_latest_rankings.csv

Creates three beginner-friendly equal-weight portfolios:
    - conservative
    - balanced
    - aggressive

Run from the project export folder:
    python models/build_portfolios.py
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.paths import MODEL_DIR

RANKINGS_FILE = MODEL_DIR / "random_forest_no_history_latest_rankings.csv"
PORTFOLIO_SIZE = 10
MAX_SECTOR_WEIGHT = 0.30
MAX_STOCK_WEIGHT = 0.20

PROFILES = {
    "conservative": {
        "max_volatility_60d": 0.35,
        "description": "Lower-volatility picks first; accepts lower expected return for a smoother ride.",
    },
    "balanced": {
        "max_volatility_60d": 0.50,
        "description": "Middle risk profile; allows more volatile stocks but still filters extreme names.",
    },
    "aggressive": {
        "max_volatility_60d": 0.80,
        "description": "Higher risk profile; allows high-volatility stocks if the model score is strong.",
    },
}


def load_rankings() -> pd.DataFrame:
    rankings = pd.read_csv(RANKINGS_FILE, parse_dates=["date"])
    rankings = rankings.sort_values("predicted_63d_return", ascending=False).reset_index(drop=True)
    return rankings


def select_portfolio(
    rankings: pd.DataFrame,
    profile: str,
    max_volatility_60d: float,
) -> tuple[pd.DataFrame, bool]:
    max_sector_count = math.floor(PORTFOLIO_SIZE * MAX_SECTOR_WEIGHT)
    max_sector_count = max(1, max_sector_count)

    eligible = rankings[rankings["volatility_60d"] <= max_volatility_60d].copy()
    relaxed = False

    # If a strict volatility cap cannot fill the portfolio, relax only the risk
    # filter while keeping diversification constraints.
    if len(eligible) < PORTFOLIO_SIZE:
        eligible = rankings.copy()
        relaxed = True

    selected: list[pd.Series] = []
    sector_counts: dict[str, int] = {}

    for _, row in eligible.iterrows():
        sector = row["sector"]
        if sector_counts.get(sector, 0) >= max_sector_count:
            continue

        selected.append(row)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

        if len(selected) == PORTFOLIO_SIZE:
            break

    if len(selected) < PORTFOLIO_SIZE and not relaxed:
        relaxed = True
        for _, row in rankings.iterrows():
            if any(existing["ticker"] == row["ticker"] for existing in selected):
                continue
            sector = row["sector"]
            if sector_counts.get(sector, 0) >= max_sector_count:
                continue
            selected.append(row)
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if len(selected) == PORTFOLIO_SIZE:
                break

    portfolio = pd.DataFrame(selected).copy()
    if portfolio.empty:
        raise ValueError(f"No stocks selected for profile {profile}.")

    portfolio.insert(0, "profile", profile)
    portfolio.insert(1, "rank", range(1, len(portfolio) + 1))
    portfolio["weight"] = 1 / len(portfolio)
    portfolio["sector_weight_after_selection"] = portfolio.groupby("sector")["weight"].transform("sum")
    portfolio["volatility_cap_relaxed"] = relaxed
    return portfolio, relaxed


def summarize_portfolio(portfolio: pd.DataFrame, description: str) -> dict[str, object]:
    weighted_return = (portfolio["predicted_63d_return"] * portfolio["weight"]).sum()
    weighted_volatility = (portfolio["volatility_60d"] * portfolio["weight"]).sum()
    weighted_momentum = (portfolio["ret_60d"] * portfolio["weight"]).sum()
    max_sector_weight = portfolio.groupby("sector")["weight"].sum().max()

    return {
        "profile": portfolio["profile"].iloc[0],
        "description": description,
        "date": portfolio["date"].max().date().isoformat(),
        "stocks": len(portfolio),
        "equal_weight": portfolio["weight"].iloc[0],
        "expected_63d_return_weighted": weighted_return,
        "avg_volatility_60d_weighted": weighted_volatility,
        "avg_ret_60d_weighted": weighted_momentum,
        "max_sector_weight": max_sector_weight,
        "sectors": portfolio["sector"].nunique(),
        "volatility_cap_relaxed": bool(portfolio["volatility_cap_relaxed"].any()),
    }


def main() -> None:
    rankings = load_rankings()

    portfolios: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    sector_rows: list[dict[str, object]] = []

    for profile, config in PROFILES.items():
        portfolio, _ = select_portfolio(rankings, profile, config["max_volatility_60d"])
        portfolios.append(portfolio)
        summaries.append(summarize_portfolio(portfolio, config["description"]))

        for sector, weight in portfolio.groupby("sector")["weight"].sum().sort_values(ascending=False).items():
            sector_rows.append({"profile": profile, "sector": sector, "weight": weight})

    all_portfolios = pd.concat(portfolios, ignore_index=True)
    summary = pd.DataFrame(summaries)
    sector_summary = pd.DataFrame(sector_rows)

    columns = [
        "profile",
        "rank",
        "date",
        "ticker",
        "sector",
        "industry",
        "weight",
        "predicted_63d_return",
        "volatility_60d",
        "ret_60d",
        "sector_weight_after_selection",
        "volatility_cap_relaxed",
    ]
    all_portfolios[columns].to_csv(MODEL_DIR / "portfolio_recommendations.csv", index=False)
    summary.to_csv(MODEL_DIR / "portfolio_summary.csv", index=False)
    sector_summary.to_csv(MODEL_DIR / "portfolio_sector_weights.csv", index=False)

    print("Portfolio construction complete")
    print(summary.to_string(index=False))
    print()
    for profile in PROFILES:
        print(f"{profile.title()} portfolio:")
        view = all_portfolios[all_portfolios["profile"] == profile][
            ["rank", "ticker", "sector", "weight", "predicted_63d_return", "volatility_60d"]
        ]
        print(view.to_string(index=False))
        print()


if __name__ == "__main__":
    main()
