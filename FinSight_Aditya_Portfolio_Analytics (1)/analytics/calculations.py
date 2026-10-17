"""
Basic, reusable financial formulas used across the analytics module.

Every function is pure (no side effects) and deterministic, so each one can be
unit-tested on its own. Values are in the portfolio's currency (₹).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

ROUND_MONEY = 2      # decimals for ₹ amounts
ROUND_PCT = 2        # decimals for percentages


def invested_value(quantity, average_buy_price):
    """Invested value = quantity × average buy price."""
    return quantity * average_buy_price


def current_value(quantity, current_price):
    """Current value = quantity × current price."""
    return quantity * current_price


def absolute_pnl(current, invested):
    """Absolute profit/loss = current value − invested value."""
    return current - invested


def return_pct(current, invested) -> Optional[float]:
    """
    Percentage return = (current − invested) / invested × 100.

    Returns None when invested is zero (return is undefined).
    Works on scalars and pandas Series.
    """
    if isinstance(invested, pd.Series):
        inv = invested.replace(0, np.nan)
        return (current - inv) / inv * 100
    if invested == 0:
        return None
    return (current - invested) / invested * 100


def weights_pct(values: pd.Series) -> pd.Series:
    """Each value as a percentage of the total. All zeros if the total is zero."""
    total = values.sum()
    if total == 0:
        return values * 0.0
    return values / total * 100


def money(x) -> Optional[float]:
    """Round to 2 decimals and convert to a plain Python float (JSON-safe)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), ROUND_MONEY)


def pct(x) -> Optional[float]:
    """Round a percentage and convert to a plain Python float (JSON-safe)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), ROUND_PCT)
