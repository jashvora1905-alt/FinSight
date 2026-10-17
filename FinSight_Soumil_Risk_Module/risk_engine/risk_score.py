"""Prototype risk scoring for FinSight.

Risk score range: 0-100, where higher values indicate greater measured risk.
The methodology is deliberately transparent and deterministic for the student prototype.
"""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .concentration import calculate_concentration
from .diversification import analyze_diversification
from .risk_metrics import calculate_historical_risk


def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _holding_concentration_risk(largest_holding_pct: float) -> float:
    # <=10% is treated as low concentration; >=60% maps to maximum component risk.
    return _bounded((largest_holding_pct - 10.0) / 50.0 * 100.0)


def _sector_concentration_risk(largest_sector_pct: float) -> float:
    # <=25% is treated as low sector concentration; >=80% maps to maximum risk.
    return _bounded((largest_sector_pct - 25.0) / 55.0 * 100.0)


def _diversification_risk(diversification_score: float) -> float:
    return _bounded(100.0 - diversification_score)


def _volatility_risk(annualized_volatility_pct: float) -> float:
    # 10% or lower -> minimal component risk; 50% or higher -> maximum.
    return _bounded((annualized_volatility_pct - 10.0) / 40.0 * 100.0)


def _drawdown_risk(maximum_drawdown_pct: float) -> float:
    dd = abs(maximum_drawdown_pct)
    # 5% or lower -> minimal component risk; 50% or worse -> maximum.
    return _bounded((dd - 5.0) / 45.0 * 100.0)


def _risk_level(score: float) -> str:
    if score <= 25:
        return "Low"
    if score <= 50:
        return "Moderate"
    if score <= 75:
        return "High"
    return "Very High"


def calculate_risk_score(
    holdings: pd.DataFrame,
    price_history: pd.DataFrame | None = None,
) -> Dict[str, Any]:
    concentration = calculate_concentration(holdings)
    diversification = analyze_diversification(holdings)
    historical = calculate_historical_risk(holdings, price_history)

    components = {
        "holding_concentration": _holding_concentration_risk(
            concentration["largest_holding_pct"]
        ),
        "sector_concentration": _sector_concentration_risk(
            concentration["largest_sector_pct"]
        ),
        "diversification_risk": _diversification_risk(
            diversification["diversification_score"]
        ),
    }

    # Base weights are used whenever history is unavailable.
    weights = {
        "holding_concentration": 0.40,
        "sector_concentration": 0.35,
        "diversification_risk": 0.25,
    }

    if historical["historical_data_available"]:
        components["volatility"] = _volatility_risk(
            historical["annualized_volatility_pct"]
        )
        components["drawdown"] = _drawdown_risk(
            historical["maximum_drawdown_pct"]
        )
        weights = {
            "holding_concentration": 0.25,
            "sector_concentration": 0.20,
            "diversification_risk": 0.15,
            "volatility": 0.25,
            "drawdown": 0.15,
        }

    score = sum(components[name] * weights[name] for name in weights)
    score = round(float(score), 2)

    return {
        "score": score,
        "level": _risk_level(score),
        "components": {k: round(float(v), 2) for k, v in components.items()},
        "component_weights": weights,
        "methodology_version": "prototype_v1",
        "higher_score_means": "higher measured portfolio risk",
    }


def analyze_portfolio_risk(
    holdings: pd.DataFrame,
    price_history: pd.DataFrame | None = None,
) -> Dict[str, Any]:
    """Main reusable output expected by the backend/Health Score Engine."""
    concentration = calculate_concentration(holdings)
    diversification = analyze_diversification(holdings)
    historical = calculate_historical_risk(holdings, price_history)
    risk_score = calculate_risk_score(holdings, price_history)

    limitations = []
    if not historical["historical_data_available"]:
        limitations.append(
            "Historical volatility, maximum drawdown and covariance-based risk "
            "contribution are unavailable because usable historical price data was not supplied."
        )
    limitations.append(
        "Prototype score thresholds are documented project assumptions and are not investment advice."
    )

    portfolio_id = None
    if "portfolio_id" in holdings.columns and not holdings.empty:
        unique_ids = holdings["portfolio_id"].dropna().astype(str).unique().tolist()
        if len(unique_ids) == 1:
            portfolio_id = unique_ids[0]

    return {
        "portfolio_id": portfolio_id,
        "concentration": concentration,
        "diversification": diversification,
        "risk_metrics": historical,
        "risk_score": risk_score,
        "limitations": limitations,
    }
