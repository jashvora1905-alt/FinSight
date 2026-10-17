"""Historical risk metrics for FinSight.

Historical price data is optional. When supplied, it must use a long format with
columns: date, symbol, close.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .concentration import _validate_holdings


PRICE_COLUMNS = {"date", "symbol", "close"}
TRADING_DAYS = 252


def _prepare_price_returns(price_history: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    if not isinstance(price_history, pd.DataFrame):
        raise TypeError("price_history must be a pandas DataFrame")
    missing = PRICE_COLUMNS.difference(price_history.columns)
    if missing:
        raise ValueError(f"Missing required historical price columns: {sorted(missing)}")

    prices = price_history.copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["symbol"] = prices["symbol"].astype(str)
    prices = prices.dropna(subset=["date", "close"])
    prices = prices[prices["symbol"].isin(symbols)]
    if prices.empty:
        raise ValueError("No historical prices match the portfolio symbols")

    pivot = (
        prices.pivot_table(index="date", columns="symbol", values="close", aggfunc="last")
        .sort_index()
        .replace([np.inf, -np.inf], np.nan)
    )
    # Require complete observations for all portfolio symbols used in covariance.
    available_symbols = [s for s in symbols if s in pivot.columns]
    if not available_symbols:
        raise ValueError("Historical prices contain none of the portfolio symbols")
    pivot = pivot[available_symbols].dropna(how="any")
    if len(pivot) < 3:
        raise ValueError("At least 3 aligned historical price observations are required")
    returns = pivot.pct_change(fill_method=None).dropna(how="any")
    if len(returns) < 2:
        raise ValueError("Insufficient historical observations to calculate returns")
    return returns


def calculate_historical_risk(
    holdings: pd.DataFrame,
    price_history: pd.DataFrame | None = None,
) -> Dict[str, Any]:
    """Calculate annualized volatility, maximum drawdown and risk contribution.

    If historical data is not supplied, deterministic 'unavailable' fields are
    returned instead of estimating or inventing values.
    """
    df = _validate_holdings(holdings)
    if price_history is None or price_history.empty:
        return {
            "historical_data_available": False,
            "annualized_volatility_pct": None,
            "maximum_drawdown_pct": None,
            "risk_contribution_pct": {},
            "observations": 0,
            "reason": "Historical price data not provided.",
        }

    symbol_values = df.groupby("symbol")["holding_value"].sum()
    weights = symbol_values / symbol_values.sum()

    try:
        returns = _prepare_price_returns(price_history, list(weights.index.astype(str)))
    except ValueError as exc:
        return {
            "historical_data_available": False,
            "annualized_volatility_pct": None,
            "maximum_drawdown_pct": None,
            "risk_contribution_pct": {},
            "observations": 0,
            "reason": str(exc),
        }

    common = [s for s in returns.columns if s in weights.index]
    common_weights = weights.loc[common].astype(float)
    common_weights = common_weights / common_weights.sum()
    returns = returns[common]

    portfolio_returns = returns.mul(common_weights, axis=1).sum(axis=1)
    daily_vol = float(portfolio_returns.std(ddof=1))
    annualized_vol = daily_vol * np.sqrt(TRADING_DAYS)

    wealth = (1.0 + portfolio_returns).cumprod()
    running_peak = wealth.cummax()
    drawdown = wealth / running_peak - 1.0
    max_drawdown = float(drawdown.min())

    cov_annual = returns.cov() * TRADING_DAYS
    w = common_weights.to_numpy(dtype=float)
    cov = cov_annual.to_numpy(dtype=float)
    portfolio_variance = float(w.T @ cov @ w)

    if portfolio_variance > 0:
        component_variance = w * (cov @ w)
        contributions = component_variance / portfolio_variance
        risk_contribution = {
            str(symbol): round(float(value * 100), 2)
            for symbol, value in zip(common, contributions)
        }
    else:
        risk_contribution = {str(symbol): 0.0 for symbol in common}

    return {
        "historical_data_available": True,
        "annualized_volatility_pct": round(float(annualized_vol * 100), 2),
        "maximum_drawdown_pct": round(float(max_drawdown * 100), 2),
        "risk_contribution_pct": risk_contribution,
        "observations": int(len(returns)),
        "symbols_used": [str(s) for s in common],
    }
