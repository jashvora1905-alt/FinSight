"""FinSight Health Score, methodology health-v1 (approved by Jash, 17 Oct 2026).

    R = 100 - risk_score.score                 (risk_engine; higher R = healthier)
    B = behavior_score.value                   (behavior; used only when status == "available")

    Health Score = 0.70 * R + 0.30 * B         when both are available   (score_basis "full",      coverage 1.00)
    Health Score = R                           when behaviour is missing (score_basis "risk_only", coverage 0.70)

Behaviour missing is an explicit, disclosed reweighting - never a silent 0 or 100 (behavior_methodology.md).
risk_score already contains diversification risk, so diversification is NOT added as a separate input (no double count).
Past returns are deliberately not scored. Nothing here recalculates a teammate's number.

Bands (aligned with risk_engine levels): >=75 Strong, >=50 Moderate, >=25 Weak, else Poor.
Informational only, not financial advice. Full rationale and sources: "FinSight Health Score: Methodology v1".
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional

METHODOLOGY_VERSION = "health-v1"
RISK_WEIGHT = 0.70
BEHAVIOR_WEIGHT = 0.30
BANDS = ((75.0, "Strong"), (50.0, "Moderate"), (25.0, "Weak"))
LOWEST_BAND = "Poor"


def band_for(score: float) -> str:
    for floor, name in BANDS:
        if score >= floor:
            return name
    return LOWEST_BAND


def _round2(value: Decimal) -> float:
    """Exact decimal arithmetic + half-up rounding, so ties such as 28.575 always give 28.58 (no binary-float noise)."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _unit_interval_100(value: Any, name: str) -> float:
    """A finite number within 0..100, otherwise ValueError (never a silent fallback)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}.")
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100, got {value}.")
    return float(value)


def compute_health_score(risk: Dict[str, Any], behavior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Pure formula on the outputs of risk_engine.analyze_portfolio_risk and behavior.analyze_behavior."""
    try:
        risk_score = _unit_interval_100(risk["risk_score"]["score"], "risk_score.score")
    except (KeyError, TypeError):
        raise ValueError("Risk output is missing risk_score.score.")
    r_value = Decimal(100) - Decimal(str(risk_score))

    b_value: Optional[Decimal] = None
    b_status = "not_provided"
    if behavior is not None:
        try:
            behavior_score = behavior["behavior_score"]
            b_status = str(behavior_score.get("status"))
            if b_status == "available":
                b_value = Decimal(str(_unit_interval_100(behavior_score["value"], "behavior_score.value")))
        except (KeyError, TypeError, AttributeError):
            raise ValueError("Behaviour output is missing behavior_score.")

    if b_value is None:
        raw_score, basis, coverage = r_value, "risk_only", RISK_WEIGHT
        w_risk, w_behavior = 1.0, 0.0
    else:
        raw_score = Decimal(str(RISK_WEIGHT)) * r_value + Decimal(str(BEHAVIOR_WEIGHT)) * b_value
        basis, coverage = "full", 1.0
        w_risk, w_behavior = RISK_WEIGHT, BEHAVIOR_WEIGHT

    score = _round2(raw_score)
    return {
        "score": score,
        "band": band_for(score),
        "score_basis": basis,
        "coverage": coverage,
        "components": {
            "risk_diversification": {
                "value": _round2(r_value),
                "weight_applied": w_risk,
                "available": True,
                "status": None,
                "source": "risk_engine.risk_score (inverted: 100 - risk score)",
            },
            "behavior": {
                "value": None if b_value is None else _round2(b_value),
                "weight_applied": w_behavior,
                "available": b_value is not None,
                "status": b_status,
                "source": "behavior.behavior_score",
            },
        },
        "methodology_version": METHODOLOGY_VERSION,
    }


def calculate_health_score(portfolio_df, transactions_df=None, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
    """DataFrame entry point (the signature the test contract expects). Runs risk_engine and behavior,
    then applies the formula. Invalid input raises ValueError (PortfolioDataError is a ValueError)."""
    from analytics import compute_holdings, load_portfolio
    from behavior import analyze_behavior
    from risk_engine import analyze_portfolio_risk

    clean, _ = load_portfolio(portfolio_df)
    if portfolio_id is not None:
        clean = clean[clean["portfolio_id"] == str(portfolio_id)].reset_index(drop=True)
    risk = analyze_portfolio_risk(compute_holdings(clean))

    behavior = None
    if transactions_df is not None and len(transactions_df) > 0:
        behavior = analyze_behavior(transactions_df.to_dict("records"), portfolio_id=portfolio_id)
    return compute_health_score(risk, behavior)
