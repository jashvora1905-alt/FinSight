"""Diversification analysis for FinSight."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .concentration import _validate_holdings, calculate_concentration


def _score_from_metrics(
    number_of_holdings: int,
    number_of_sectors: int,
    largest_holding_pct: float,
    largest_sector_pct: float,
) -> float:
    """Return a transparent 0-100 diversification score (higher is better)."""
    # Breadth rewards are capped so very large portfolios do not dominate the score.
    holdings_score = min(number_of_holdings / 10.0, 1.0) * 30.0
    sectors_score = min(number_of_sectors / 5.0, 1.0) * 25.0

    # Concentration penalties are converted into 'quality' scores.
    holding_quality = max(0.0, min(1.0, (60.0 - largest_holding_pct) / 50.0)) * 25.0
    sector_quality = max(0.0, min(1.0, (80.0 - largest_sector_pct) / 60.0)) * 20.0

    return round(holdings_score + sectors_score + holding_quality + sector_quality, 2)


def _level(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    if score >= 25:
        return "Low"
    return "Very Low"


def analyze_diversification(holdings: pd.DataFrame) -> Dict[str, Any]:
    df = _validate_holdings(holdings)
    concentration = calculate_concentration(df)

    number_of_holdings = int(df["symbol"].nunique())
    number_of_sectors = int(df["sector"].nunique())
    effective_holdings = round(1.0 / concentration["holding_hhi"], 2)
    effective_sectors = round(1.0 / concentration["sector_hhi"], 2)

    score = _score_from_metrics(
        number_of_holdings,
        number_of_sectors,
        concentration["largest_holding_pct"],
        concentration["largest_sector_pct"],
    )

    gaps = []
    if number_of_holdings < 5:
        gaps.append("Portfolio has fewer than 5 distinct holdings.")
    if number_of_sectors < 3:
        gaps.append("Portfolio is exposed to fewer than 3 sectors.")
    if concentration["largest_holding_pct"] > 35:
        gaps.append("A single holding exceeds 35% of current portfolio value.")
    if concentration["largest_sector_pct"] > 50:
        gaps.append("A single sector exceeds 50% of current portfolio value.")

    return {
        "number_of_holdings": number_of_holdings,
        "number_of_sectors": number_of_sectors,
        "effective_holdings": effective_holdings,
        "effective_sectors": effective_sectors,
        "diversification_score": score,
        "diversification_level": _level(score),
        "diversification_gaps": gaps,
    }
