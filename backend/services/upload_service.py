"""CSV upload: read -> validate (via the analysis modules) -> store -> return the analysis."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional

import pandas as pd

from analytics import load_portfolio
from behavior.transaction_analysis import REQUIRED_FIELDS as TRANSACTION_FIELDS

from ..database import repository
from ..models import Holding, Portfolio, PricePoint, Transaction
from .analysis_service import run_analysis
from .errors import ApiError


def decode_csv(raw: bytes, field: str) -> str:
    if not raw or not raw.strip():
        raise ApiError(422, f"The '{field}' file is empty.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiError(422, f"The '{field}' file must be a UTF-8 encoded CSV.")


def _read_frame(text: str, field: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(text))
    except pd.errors.EmptyDataError:
        raise ApiError(422, f"The '{field}' file is empty.")
    except (pd.errors.ParserError, ValueError) as exc:
        raise ApiError(422, f"The '{field}' file is not a valid CSV: {exc}")


def _read_transactions(text: str) -> List[dict]:
    reader = csv.DictReader(io.StringIO(text))
    missing = set(TRANSACTION_FIELDS) - set(reader.fieldnames or [])
    if missing:
        raise ApiError(422, "Transactions file is missing columns: " + ", ".join(sorted(missing)))
    try:
        return list(reader)
    except csv.Error as exc:
        raise ApiError(422, f"The 'transactions' file is not a valid CSV: {exc}")


def _portfolio_rows(df: pd.DataFrame) -> pd.DataFrame:
    """The raw uploaded rows in the shape the loader sees them (same column handling as analytics.load_portfolio),
    so that re-analysing the stored rows reproduces the upload's analysis exactly, warnings included."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    out = out[repository.HOLDING_COLUMNS].dropna(how="all")
    return out


def process_upload(portfolio_text: str, transactions_text: Optional[str], price_text: Optional[str],
                   portfolio_id: Optional[str], observation_start: Optional[str],
                   observation_end: Optional[str]) -> Dict[str, Any]:
    portfolio_df = _read_frame(portfolio_text, "portfolio")
    transactions = _read_transactions(transactions_text) if transactions_text else None
    price_history = _read_frame(price_text, "price_history") if price_text else None
    if price_history is not None:  # same column handling on upload and on read-back, so results always match
        price_history.columns = [str(c).strip().lower() for c in price_history.columns]

    result = run_analysis(portfolio_df, transactions or None, price_history, portfolio_id,
                          observation_start, observation_end)  # validates everything before anything is stored

    rows = _portfolio_rows(portfolio_df)
    if rows["portfolio_id"].isna().any() or (rows["portfolio_id"].astype(str).str.strip() == "").any():
        raise ApiError(422, "Every holding row must have a portfolio_id.")
    rows["portfolio_id"] = rows["portfolio_id"].astype(str).str.strip()
    if portfolio_id is not None:
        rows = rows[rows["portfolio_id"] == str(portfolio_id)]
    ids = list(dict.fromkeys(rows["portfolio_id"]))

    tx_rows = [t for t in (transactions or []) if str(t.get("portfolio_id", "")).strip() in ids]
    unknown = sorted({str(t.get("portfolio_id", "")).strip() for t in (transactions or [])} - set(ids))
    if unknown and portfolio_id is None:
        raise ApiError(422, "Transactions reference portfolio_id(s) not present in the portfolio file: "
                            + ", ".join(unknown))

    # Price history is kept only if it has the date/symbol/close columns; otherwise the risk engine has already
    # reported it as unusable and there is nothing meaningful to store.
    price_rows = (price_history[["date", "symbol", "close"]].to_dict("records")
                  if price_history is not None and {"date", "symbol", "close"} <= set(price_history.columns) else [])

    # one upload replaces everything stored for these portfolio ids
    repository.replace_portfolios(
        [Portfolio(id=i, observation_start=observation_start, observation_end=observation_end) for i in ids],
        [Holding(**{c: r[c] for c in repository.HOLDING_COLUMNS}) for r in rows.to_dict("records")],
        [Transaction(portfolio_id=str(t["portfolio_id"]).strip(), transaction_id=t.get("transaction_id"),
                     date=t.get("date"), symbol=t.get("symbol"), transaction_type=t.get("transaction_type"),
                     quantity=t.get("quantity"), price=t.get("price")) for t in tx_rows],
        [PricePoint(portfolio_id=i, date=r["date"], symbol=r["symbol"], close=r["close"])
         for i in ids for r in price_rows],
    )
    return {
        "portfolio_id": result["analytics"]["portfolio_id"],
        "portfolio_ids": ids,
        "inputs": {"transactions_provided": bool(transactions), "price_history_provided": price_history is not None},
        **result,
    }

