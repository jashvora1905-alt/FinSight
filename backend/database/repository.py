"""All SQL lives here. Uploads REPLACE the stored data of every portfolio_id they contain, so a stored portfolio
always equals its latest upload (holdings + transactions + price history)."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Sequence

import pandas as pd

from ..models import Holding, Portfolio, PricePoint, Transaction
from .connection import connect

HOLDING_COLUMNS = ["portfolio_id", "symbol", "company_name", "asset_type", "sector",
                   "quantity", "average_buy_price", "current_price"]
TRANSACTION_COLUMNS = ["transaction_id", "portfolio_id", "date", "symbol", "transaction_type", "quantity", "price"]


def _clean(value: Any) -> Any:
    """NaN/None -> NULL; numpy scalars -> plain Python."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
        if isinstance(value, float) and math.isnan(value):
            return None
    return value


def _num(value: Any) -> Optional[float]:
    value = _clean(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None  # non-numeric text never reaches storage: the analysis modules reject it first


def _text(value: Any) -> Optional[str]:
    value = _clean(value)
    return None if value is None else str(value)


def replace_portfolios(portfolios: Sequence[Portfolio], holdings: Iterable[Holding],
                       transactions: Iterable[Transaction], prices: Iterable[PricePoint]) -> None:
    """Delete any existing portfolio with the same ids (rows cascade) and insert the new data atomically."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")  # one stamp per upload = one batch
    conn = connect()
    try:
        with conn:
            for p in portfolios:
                conn.execute("DELETE FROM portfolios WHERE id = ?", (p.id,))
                conn.execute(
                    "INSERT INTO portfolios (id, user_id, name, observation_start, observation_end, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (p.id, p.user_id, p.name or p.id, p.observation_start, p.observation_end, stamp))
            conn.executemany(
                "INSERT INTO holdings (portfolio_id, symbol, company_name, asset_type, sector, quantity, "
                "average_buy_price, current_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(h.portfolio_id, _text(h.symbol), _text(h.company_name), _text(h.asset_type), _text(h.sector),
                  _num(h.quantity), _num(h.average_buy_price), _num(h.current_price)) for h in holdings])
            conn.executemany(
                "INSERT INTO transactions (transaction_id, portfolio_id, date, symbol, transaction_type, quantity, price) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(_text(t.transaction_id), t.portfolio_id, _text(t.date), _text(t.symbol),
                  _text(t.transaction_type), _num(t.quantity), _num(t.price)) for t in transactions])
            conn.executemany(
                "INSERT INTO price_history (portfolio_id, date, symbol, close) VALUES (?, ?, ?, ?)",
                [(p.portfolio_id, _text(p.date), _text(p.symbol), _num(p.close)) for p in prices])
    finally:
        conn.close()


def latest_portfolio_ids() -> list[str]:
    """Portfolios written by the most recent upload (they share one created_at stamp)."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id FROM portfolios WHERE created_at = (SELECT MAX(created_at) FROM portfolios) ORDER BY rowid"
        ).fetchall()
    finally:
        conn.close()
    return [r["id"] for r in rows]


def portfolio_exists(portfolio_id: str) -> bool:
    conn = connect()
    try:
        return conn.execute("SELECT 1 FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone() is not None
    finally:
        conn.close()


def load_scope(ids: Sequence[str]) -> dict:
    """Everything stored for these portfolio ids, in original upload order, ready for the analysis modules."""
    marks = ",".join("?" for _ in ids)
    conn = connect()
    try:
        h = conn.execute(f"SELECT {', '.join(HOLDING_COLUMNS)} FROM holdings WHERE portfolio_id IN ({marks}) ORDER BY id",
                         list(ids)).fetchall()
        t = conn.execute(f"SELECT {', '.join(TRANSACTION_COLUMNS)} FROM transactions WHERE portfolio_id IN ({marks}) ORDER BY id",
                         list(ids)).fetchall()
        p = conn.execute(f"SELECT date, symbol, close FROM price_history WHERE portfolio_id IN ({marks}) "
                         f"GROUP BY date, symbol, close ORDER BY MIN(id)", list(ids)).fetchall()
        o = conn.execute(f"SELECT observation_start, observation_end FROM portfolios WHERE id IN ({marks}) ORDER BY rowid LIMIT 1",
                         list(ids)).fetchone()
    finally:
        conn.close()
    return {
        "holdings": pd.DataFrame([tuple(r) for r in h], columns=HOLDING_COLUMNS),
        "transactions": [dict(r) for r in t] or None,
        "price_history": pd.DataFrame([tuple(r) for r in p], columns=["date", "symbol", "close"]) if p else None,
        "observation_start": o["observation_start"] if o else None,
        "observation_end": o["observation_end"] if o else None,
    }
