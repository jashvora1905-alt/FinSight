"""
FinSight Portfolio Analytics (owner: Aditya Shah, branch feature/portfolio-analytics).

Main entry point for the backend:

    from analytics import analyze_portfolio
    result = analyze_portfolio("data/sample_portfolio.csv", portfolio_id="P001")

Lower-level pieces (for the Risk, Health Score and API modules):

    from analytics import load_portfolio, compute_holdings
    df, warnings = load_portfolio("data/sample_portfolio.csv")
    holdings = compute_holdings(df)   # DataFrame with invested/current value, P&L, weights
"""

from .allocation import allocation_by, allocation_summary
from .calculations import absolute_pnl, current_value, invested_value, return_pct
from .performance import holding_performance, portfolio_performance
from .portfolio_metrics import (
    PortfolioDataError,
    analyze_portfolio,
    compute_holdings,
    load_portfolio,
    portfolio_totals,
    validate_portfolio,
)

__all__ = [
    "analyze_portfolio",
    "load_portfolio",
    "validate_portfolio",
    "compute_holdings",
    "portfolio_totals",
    "PortfolioDataError",
    "holding_performance",
    "portfolio_performance",
    "allocation_by",
    "allocation_summary",
    "invested_value",
    "current_value",
    "absolute_pnl",
    "return_pct",
]
