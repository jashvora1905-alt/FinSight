"""
Asset, sector and security allocation.

Weights are based on CURRENT value (what the portfolio looks like today).
Invested-value weights are included too, so the dashboard can show how the
mix has drifted from what was originally bought.

Concentration metrics (largest holding %, top-3 %, HHI) and diversification
judgements belong to the Risk & Diversification module (risk_engine/) and
are deliberately not duplicated here. Lists are sorted largest first, so the
dashboard can still read the biggest sector/holding from index 0.
"""

from __future__ import annotations

import pandas as pd

from .calculations import money, pct, return_pct, weights_pct


def allocation_by(holdings: pd.DataFrame, column: str) -> list[dict]:
    """Group holdings by `column` and return allocation rows, largest first."""
    g = holdings.groupby(column, sort=False).agg(
        current_value=("current_value", "sum"),
        invested_value=("invested_value", "sum"),
        pnl=("pnl", "sum"),
        holdings=("symbol", "count"),
    )
    g["weight_pct"] = weights_pct(g["current_value"])
    g["invested_weight_pct"] = weights_pct(g["invested_value"])
    g["return_pct"] = return_pct(g["current_value"], g["invested_value"])
    g = g.sort_values("current_value", ascending=False)

    return [{
        "name": str(name),
        "current_value": money(r.current_value),
        "invested_value": money(r.invested_value),
        "weight_pct": pct(r.weight_pct),
        "invested_weight_pct": pct(r.invested_weight_pct),
        "drift_pct": pct(r.weight_pct - r.invested_weight_pct),
        "pnl": money(r.pnl),
        "return_pct": pct(r.return_pct),
        "holdings": int(r.holdings),
    } for name, r in g.iterrows()]


def allocation_summary(holdings: pd.DataFrame) -> dict:
    """Allocation across asset types, sectors and individual securities."""
    by_asset = allocation_by(holdings, "asset_type")
    by_sector = allocation_by(holdings, "sector")
    by_security = allocation_by(holdings, "symbol")
    return {
        "basis": "current_value",
        "by_asset_type": by_asset,
        "by_sector": by_sector,
        "by_security": by_security,
        "number_of_asset_types": len(by_asset),
        "number_of_sectors": len(by_sector),
    }
