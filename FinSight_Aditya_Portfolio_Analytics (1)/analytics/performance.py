"""
Stock-level and portfolio-level performance.
"""

from __future__ import annotations

import pandas as pd

from .calculations import money, pct

TOP_N = 3


def holding_performance(holdings: pd.DataFrame) -> list[dict]:
    """
    One record per holding, largest position first.

    contribution_pct = holding P&L / total portfolio invested value × 100.
    The contributions of all holdings add up to the portfolio return %.
    """
    total_invested = holdings["invested_value"].sum()
    rows = []
    for h in holdings.sort_values("current_value", ascending=False).itertuples(index=False):
        rows.append({
            "symbol": h.symbol,
            "company_name": h.company_name,
            "asset_type": h.asset_type,
            "sector": h.sector,
            "quantity": float(h.quantity),
            "average_buy_price": money(h.average_buy_price),
            "current_price": money(h.current_price),
            "invested_value": money(h.invested_value),
            "current_value": money(h.current_value),
            "pnl": money(h.pnl),
            "return_pct": pct(h.return_pct),
            "weight_pct": pct(h.weight_pct),
            "contribution_pct": pct(h.pnl / total_invested * 100) if total_invested else None,
            "status": "gain" if h.pnl > 0 else "loss" if h.pnl < 0 else "flat",
            "price_missing": bool(h.price_missing),
        })
    return rows


def _ranked(holdings: pd.DataFrame, column: str, ascending: bool, keep) -> list[dict]:
    subset = holdings[keep].sort_values(column, ascending=ascending).head(TOP_N)
    return [
        {"symbol": r.symbol, "return_pct": pct(r.return_pct), "pnl": money(r.pnl)}
        for r in subset.itertuples(index=False)
    ]


def portfolio_performance(holdings: pd.DataFrame, totals: dict) -> dict:
    """Portfolio summary: totals, win/loss counts, best and worst holdings."""
    gainers = holdings["pnl"] > 0
    losers = holdings["pnl"] < 0
    return {
        "invested_value": money(totals["invested_value"]),
        "current_value": money(totals["current_value"]),
        "pnl": money(totals["pnl"]),
        "return_pct": pct(totals["return_pct"]),
        "status": "gain" if totals["pnl"] > 0 else "loss" if totals["pnl"] < 0 else "flat",
        "number_of_holdings": int(len(holdings)),
        "gainers": int(gainers.sum()),
        "losers": int(losers.sum()),
        "unchanged": int((holdings["pnl"] == 0).sum()),
        "total_gains": money(holdings.loc[gainers, "pnl"].sum()),
        "total_losses": money(holdings.loc[losers, "pnl"].sum()),
        "top_gainers": _ranked(holdings, "return_pct", False, gainers),
        "top_losers": _ranked(holdings, "return_pct", True, losers),
        "largest_pnl_contributor": (_ranked(holdings, "pnl", False, gainers) or [None])[0],
        "largest_pnl_detractor": (_ranked(holdings, "pnl", True, losers) or [None])[0],
    }
