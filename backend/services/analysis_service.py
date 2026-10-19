"""Glue between stored/uploaded data and the teammates' modules. No financial logic lives here:
analytics, risk_engine, behavior and the Health Score engine do all the calculating."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from analytics import PortfolioDataError, analyze_portfolio, compute_holdings, load_portfolio
from behavior import analyze_behavior
from risk_engine import analyze_portfolio_risk

from ..database import repository
from .errors import ApiError
from .health_score import compute_health_score


def run_analysis(portfolio_df: pd.DataFrame, transactions: Optional[List[dict]] = None,
                 price_history: Optional[pd.DataFrame] = None, portfolio_id: Optional[str] = None,
                 observation_start: Optional[str] = None, observation_end: Optional[str] = None) -> Dict[str, Any]:
    """analytics + risk + (if transactions) behaviour + health score. Bad input -> ApiError(422)."""
    try:
        analytics = analyze_portfolio(portfolio_df, portfolio_id=portfolio_id)
        clean, _ = load_portfolio(portfolio_df)
        if portfolio_id is not None:
            clean = clean[clean["portfolio_id"] == str(portfolio_id)].reset_index(drop=True)
        risk = analyze_portfolio_risk(compute_holdings(clean), price_history)
    except (PortfolioDataError, ValueError) as exc:  # risk_engine signals bad input with ValueError
        raise ApiError(422, str(exc))

    behavior: Optional[dict] = None
    if transactions:
        try:
            behavior = analyze_behavior(transactions, portfolio_id=portfolio_id,
                                        observation_start=observation_start, observation_end=observation_end)
        except ValueError as exc:
            raise ApiError(422, f"Transactions: {exc}")

    # Outside the try-blocks on purpose: bad *input* is a 422, but a ValueError here means a module returned an
    # unexpected shape, which is a server bug (500), not a client error.
    return {"analytics": analytics, "risk": risk, "behavior": behavior,
            "health_score": compute_health_score(analytics, risk, behavior)}


def analysis_for(portfolio_id: Optional[str]) -> Dict[str, Any]:
    """Analysis of a stored portfolio, or (no id) of the portfolios written by the most recent upload."""
    if portfolio_id is None:
        ids = repository.latest_portfolio_ids()
        if not ids:
            raise ApiError(404, "No portfolio has been uploaded yet. POST /api/portfolio/upload first.")
    else:
        if not repository.portfolio_exists(portfolio_id):
            raise ApiError(404, f"Portfolio '{portfolio_id}' not found.")
        ids = [portfolio_id]
    data = repository.load_scope(ids)
    return run_analysis(data["holdings"], data["transactions"], data["price_history"], portfolio_id,
                        data["observation_start"], data["observation_end"])
