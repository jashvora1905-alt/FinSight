"""Glue between the uploaded CSV text and the teammates' modules. No financial logic lives
here: analytics, risk_engine and behavior do all the calculating."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, Optional

import pandas as pd

from analytics import PortfolioDataError, analyze_portfolio, compute_holdings, load_portfolio
from behavior import analyze_behavior
from behavior.transaction_analysis import REQUIRED_FIELDS as TRANSACTION_FIELDS
from risk_engine import analyze_portfolio_risk

from .errors import ApiError
from .health_score import compute_health_score
from .store import Upload


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


def _read_transactions(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    missing = set(TRANSACTION_FIELDS) - set(reader.fieldnames or [])
    if missing:
        raise ApiError(422, "Transactions file is missing columns: " + ", ".join(sorted(missing)))
    try:
        return list(reader)
    except csv.Error as exc:
        raise ApiError(422, f"The 'transactions' file is not a valid CSV: {exc}")


def run_analysis(u: Upload) -> Dict[str, Any]:
    """Run analytics, risk and (if transactions were uploaded) behaviour on a stored upload."""
    portfolio_df = _read_frame(u.portfolio_csv, "portfolio")

    try:
        analytics = analyze_portfolio(portfolio_df, portfolio_id=u.portfolio_id)
        clean, _ = load_portfolio(portfolio_df)
        if u.portfolio_id is not None:
            clean = clean[clean["portfolio_id"] == str(u.portfolio_id)].reset_index(drop=True)
        price_history = _read_frame(u.price_history_csv, "price_history") if u.price_history_csv else None
        risk = analyze_portfolio_risk(compute_holdings(clean), price_history)
    except PortfolioDataError as exc:
        raise ApiError(422, str(exc))
    except ValueError as exc:  # risk_engine signals bad input with ValueError
        raise ApiError(422, str(exc))

    behavior: Optional[dict] = None
    if u.transactions_csv:
        try:
            behavior = analyze_behavior(
                _read_transactions(u.transactions_csv),
                portfolio_id=u.portfolio_id,
                observation_start=u.observation_start,
                observation_end=u.observation_end,
            )
        except ValueError as exc:
            raise ApiError(422, f"Transactions: {exc}")

    # Outside the try-blocks above on purpose: bad *input* is a 422, but a ValueError here would mean a
    # module returned an unexpected shape, which is a server bug (500), not a client error.
    return {"analytics": analytics, "risk": risk, "behavior": behavior,
            "health_score": compute_health_score(risk, behavior)}
