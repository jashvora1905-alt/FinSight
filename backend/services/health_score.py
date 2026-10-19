"""FinSight Health Score, methodology health-v2 (README: Portfolio Health Score).

README dimensions: Performance, Risk, Diversification, Behaviour. Each is a 0-100 component, higher = healthier:

    performance     = clamp(50 + 50 * return_pct / 30, 0, 100)     analytics summary.return_pct (since purchase)
    risk            = 100 - risk_ex_div                            risk_engine components WITHOUT diversification_risk,
                                                                   re-weighted to sum to 1 (diversification is scored
                                                                   on its own, so it is not counted twice)
    diversification = diversification_score                        risk_engine
    behavior        = behavior_score.value                         behavior, only when status == "available"

    base weights:  risk 0.35 | diversification 0.25 | behavior 0.25 | performance 0.15
    score = sum(applied_weight * component),  applied_weight = base_weight / sum(base weights of AVAILABLE components)

A missing component (no transactions, too little history, no return) is never replaced by a made-up value: the
remaining weights are rescaled, score_basis becomes "partial" and coverage < 1 (the share of base weight scored).
points_lost = applied_weight * (100 - component); score = 100 - sum(points_lost).

Bands: >= 75 Strong, >= 50 Moderate, >= 25 Weak, else Poor. Exact decimal arithmetic, half-up rounding to 2 dp.
Nothing here recalculates a teammate's base metric. Informational only, not financial advice.
Rationale, sources and validation: docs/health_score_methodology.md.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

METHODOLOGY_VERSION = "health-v2"
BASE_WEIGHTS = {"risk": Decimal("0.35"), "diversification": Decimal("0.25"),
                "behavior": Decimal("0.25"), "performance": Decimal("0.15")}
LABELS = {"performance": "Performance", "risk": "Risk", "diversification": "Diversification", "behavior": "Behaviour"}
ORDER = ("performance", "risk", "diversification", "behavior")  # README order
PERFORMANCE_FULL_SCALE_PCT = Decimal("30")  # return since purchase of -30% -> 0, 0% -> 50, +30% or more -> 100
BANDS = ((Decimal("75"), "Strong"), (Decimal("50"), "Moderate"), (Decimal("25"), "Weak"))
LOWEST_BAND = "Poor"
HUNDRED = Decimal(100)


def _round2(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def band_for(score: float) -> str:
    value = Decimal(str(score))
    for floor, name in BANDS:
        if value >= floor:
            return name
    return LOWEST_BAND


def _finite(value: Any, name: str, lo: Optional[float] = None, hi: Optional[float] = None) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}.")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise ValueError(f"{name} must be between {lo} and {hi}, got {value}.")
    return Decimal(str(value))


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal(0), min(HUNDRED, value))


def _performance(analytics: Dict[str, Any]) -> Optional[Decimal]:
    try:
        ret = analytics["summary"]["return_pct"]
    except (KeyError, TypeError):
        raise ValueError("Analytics output is missing summary.return_pct.")
    if ret is None:
        return None
    return _clamp(Decimal(50) + Decimal(50) * _finite(ret, "summary.return_pct") / PERFORMANCE_FULL_SCALE_PCT)


def _risk(risk: Dict[str, Any]) -> Decimal:
    try:
        components = risk["risk_score"]["components"]
        weights = risk["risk_score"]["component_weights"]
        names = [k for k in weights if k != "diversification_risk"] or list(weights)
        total = sum(Decimal(str(weights[k])) for k in names)
        risk_ex = sum(Decimal(str(weights[k])) * _finite(components[k], f"risk component {k}", 0, 100)
                      for k in names) / total
    except (KeyError, TypeError, ZeroDivisionError, AttributeError):
        raise ValueError("Risk output is missing risk_score components or weights.")
    return HUNDRED - risk_ex


def _diversification(risk: Dict[str, Any]) -> Decimal:
    try:
        return _finite(risk["diversification"]["diversification_score"], "diversification_score", 0, 100)
    except (KeyError, TypeError):
        raise ValueError("Risk output is missing diversification.diversification_score.")


def _behavior(behavior: Optional[Dict[str, Any]]):
    """-> (value or None, status, reasons)"""
    if behavior is None:
        return None, "not_provided", []
    try:
        score = behavior["behavior_score"]
        status = str(score.get("status"))
        reasons = list(score.get("reasons") or [])
        if status == "available":
            return _finite(score["value"], "behavior_score.value", 0, 100), status, reasons
        return None, status, reasons
    except (KeyError, TypeError, AttributeError):
        raise ValueError("Behaviour output is missing behavior_score.")


def compute_health_score(analytics: Dict[str, Any], risk: Dict[str, Any],
                         behavior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Pure formula on the outputs of analytics.analyze_portfolio, risk_engine.analyze_portfolio_risk and
    behavior.analyze_behavior. Invalid or malformed module output raises ValueError (never a silent fallback)."""
    b_value, b_status, b_reasons = _behavior(behavior)
    perf = _performance(analytics)
    values: Dict[str, Optional[Decimal]] = {
        "performance": perf, "risk": _risk(risk), "diversification": _diversification(risk), "behavior": b_value}
    status = {"performance": "available" if perf is not None else "unavailable",
              "risk": "available", "diversification": "available", "behavior": b_status}

    available = [k for k in ORDER if values[k] is not None]
    coverage = sum(BASE_WEIGHTS[k] for k in available)
    applied = {k: (BASE_WEIGHTS[k] / coverage if k in available else Decimal(0)) for k in ORDER}
    score_exact = sum(applied[k] * values[k] for k in available)
    score = _round2(score_exact)
    band = band_for(score)

    components: Dict[str, Any] = {}
    for k in ORDER:
        v = values[k]
        components[k] = {
            "label": LABELS[k],
            "value": None if v is None else _round2(v),
            "base_weight": float(BASE_WEIGHTS[k]),
            "weight_applied": _round2(applied[k]) if k in available else 0.0,
            "available": v is not None,
            "status": status[k],
            "contribution_points": None if v is None else _round2(applied[k] * v),
            "points_lost": None if v is None else _round2(applied[k] * (HUNDRED - v)),
            "source": {"performance": "analytics.summary.return_pct",
                       "risk": "risk_engine.risk_score components excluding diversification_risk (inverted)",
                       "diversification": "risk_engine.diversification.diversification_score",
                       "behavior": "behavior.behavior_score"}[k],
        }

    missing = [k for k in ORDER if k not in available]
    drivers = sorted(
        ({"component": k, "label": LABELS[k], "value": components[k]["value"],
          "weight_applied": components[k]["weight_applied"], "points_lost": components[k]["points_lost"]}
         for k in available),
        key=lambda d: (-d["points_lost"], ORDER.index(d["component"])))

    notes: List[str] = []
    if missing:
        names = ", ".join(LABELS[k] for k in missing)
        notes.append(f"Provisional score: {names} could not be scored, so the remaining weights were rescaled "
                     f"(coverage {_round2(coverage * 100):g}%).")
    if "behavior" in missing:
        notes.append("No transaction history was provided." if b_status == "not_provided"
                     else f"Behaviour score unavailable ({b_status}).")
        notes.extend(f"Behaviour: {r}" for r in b_reasons)
    if "performance" in missing:
        notes.append("Performance unavailable: no return could be computed.")
    try:
        notes.extend(f"Diversification: {g}" for g in risk["diversification"].get("diversification_gaps", []))
        if risk.get("risk_metrics", {}).get("historical_data_available") is False:
            notes.append("Risk reflects concentration only: no historical price data was supplied "
                         "(volatility and drawdown not measured).")
    except AttributeError:
        pass
    try:
        n_missing_price = sum(1 for h in analytics.get("holdings", []) if h.get("price_missing"))
        if n_missing_price:
            notes.append(f"Performance used the average buy price for {n_missing_price} holding(s) with no "
                         f"current price (their gain or loss is shown as zero).")
    except AttributeError:
        pass

    top = drivers[0]
    summary = f"Health score {score:.2f} ({band})."
    if top["points_lost"] > 0:
        summary += f" Largest drag: {top['label']} ({top['points_lost']:.2f} points below its maximum)."
    if missing:
        summary += " Provisional."

    return {
        "score": score,
        "band": band,
        "score_basis": "full" if not missing else "partial",
        "coverage": _round2(coverage),
        "missing_components": missing,
        "components": components,
        "explanation": {"summary": summary, "drivers": drivers, "notes": notes},
        "methodology_version": METHODOLOGY_VERSION,
    }


def calculate_health_score(portfolio_df, transactions_df=None, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
    """DataFrame entry point (the signature the test contract expects): runs analytics, risk_engine and behavior,
    then applies the formula. Invalid input raises ValueError (PortfolioDataError is a ValueError)."""
    from analytics import analyze_portfolio, compute_holdings, load_portfolio
    from behavior import analyze_behavior
    from risk_engine import analyze_portfolio_risk

    analytics = analyze_portfolio(portfolio_df, portfolio_id=portfolio_id)
    clean, _ = load_portfolio(portfolio_df)
    if portfolio_id is not None:
        clean = clean[clean["portfolio_id"] == str(portfolio_id)].reset_index(drop=True)
    risk = analyze_portfolio_risk(compute_holdings(clean))
    behavior = None
    if transactions_df is not None and len(transactions_df) > 0:
        behavior = analyze_behavior(transactions_df.to_dict("records"), portfolio_id=portfolio_id)
    return compute_health_score(analytics, risk, behavior)
