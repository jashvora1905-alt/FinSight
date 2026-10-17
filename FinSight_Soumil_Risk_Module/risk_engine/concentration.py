"""Concentration metrics for the FinSight risk engine.

All functions are deterministic and operate only on supplied portfolio data.
Expected holdings columns (minimum): symbol, sector, quantity, current_price.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"symbol", "sector", "quantity", "current_price"}


def _validate_holdings(holdings: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(holdings, pd.DataFrame):
        raise TypeError("holdings must be a pandas DataFrame")
    missing = REQUIRED_COLUMNS.difference(holdings.columns)
    if missing:
        raise ValueError(f"Missing required portfolio columns: {sorted(missing)}")
    if holdings.empty:
        raise ValueError("Portfolio contains no holdings")

    df = holdings.copy()
    for col in ("quantity", "current_price"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["quantity", "current_price"]].isna().any().any():
        raise ValueError("quantity and current_price must contain valid numeric values")
    if (df["quantity"] < 0).any() or (df["current_price"] < 0).any():
        raise ValueError("quantity and current_price cannot be negative")

    df["sector"] = df["sector"].fillna("Unknown").astype(str)
    df["symbol"] = df["symbol"].astype(str)
    df["holding_value"] = df["quantity"] * df["current_price"]
    total = float(df["holding_value"].sum())
    if total <= 0:
        raise ValueError("Total current portfolio value must be greater than zero")
    df["weight"] = df["holding_value"] / total
    return df


def calculate_concentration(holdings: pd.DataFrame) -> Dict[str, Any]:
    """Calculate holding and sector concentration metrics.

    HHI is sum(weight^2), ranging from 1/n for an equal-weight portfolio to 1.0
    for a single holding/sector. Percent fields are returned on a 0-100 scale.
    """
    df = _validate_holdings(holdings)

    holding_weights = (
        df.groupby("symbol", as_index=True)["holding_value"].sum()
        / df["holding_value"].sum()
    ).sort_values(ascending=False)
    sector_weights = (
        df.groupby("sector", as_index=True)["holding_value"].sum()
        / df["holding_value"].sum()
    ).sort_values(ascending=False)

    holding_hhi = float(np.square(holding_weights.to_numpy()).sum())
    sector_hhi = float(np.square(sector_weights.to_numpy()).sum())

    return {
        "largest_holding_pct": round(float(holding_weights.iloc[0] * 100), 2),
        "top_3_holdings_pct": round(float(holding_weights.head(3).sum() * 100), 2),
        "holding_hhi": round(holding_hhi, 6),
        "largest_sector_pct": round(float(sector_weights.iloc[0] * 100), 2),
        "sector_hhi": round(sector_hhi, 6),
        "holding_weights_pct": {
            str(k): round(float(v * 100), 2) for k, v in holding_weights.items()
        },
        "sector_weights_pct": {
            str(k): round(float(v * 100), 2) for k, v in sector_weights.items()
        },
    }
