"""Strict reference validators for the shared schemas. Return a list of error strings ([] = valid).

These are deliberately STRICTER than the delivered modules (e.g. duplicates, zero quantity and zero
current price are errors here but only warnings in analytics). They define what clean demo data
looks like; tests of module behaviour assert what the modules actually do (see *_reference tests).
"""
import re

import pandas as pd

PORTFOLIO_COLUMNS = ["portfolio_id", "symbol", "company_name", "asset_type", "sector",
                     "quantity", "average_buy_price", "current_price"]
TRANSACTION_COLUMNS = ["transaction_id", "portfolio_id", "date", "symbol",
                       "transaction_type", "quantity", "price"]
# Modules accept any text for asset_type; this vocabulary is only enforced on OUR sample data
# (check_asset_types), not on user uploads.
ASSET_TYPES = {"Equity", "ETF", "Mutual Fund", "Bond", "Gold", "Cash"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _missing(df, cols):
    m = [c for c in cols if c not in df.columns]
    return [f"missing columns: {m}"] if m else []


def check_asset_types(df):
    return [] if df["asset_type"].isin(ASSET_TYPES).all() else ["unknown asset_type"]


def validate_portfolio(df):
    errs = _missing(df, PORTFOLIO_COLUMNS)
    if errs:
        return errs
    if df.empty:
        return ["no rows"]
    for col in ("portfolio_id", "symbol"):
        if df[col].isna().any() or (df[col].astype(str).str.strip() == "").any():
            errs.append(f"blank {col}")
    for c in ["quantity", "average_buy_price", "current_price"]:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.isna().any():
            errs.append(f"non-numeric {c}")
        elif (s <= 0).any():
            errs.append(f"non-positive {c}")
    if df.duplicated(subset=["portfolio_id", "symbol"]).any():
        errs.append("duplicate symbols")
    return errs


def validate_transactions(df):
    errs = _missing(df, TRANSACTION_COLUMNS)
    if errs:
        return errs
    if df.empty:
        return ["no rows"]
    if df["portfolio_id"].isna().any():
        errs.append("blank portfolio_id")
    if not df["transaction_type"].isin(["BUY", "SELL"]).all():
        errs.append("invalid transaction_type")
    dates = df["date"].astype(str)
    parsed = pd.to_datetime(dates, format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any() or not dates.map(lambda d: bool(_DATE.match(d))).all():
        errs.append("invalid date")
    for c in ["quantity", "price"]:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.isna().any():
            errs.append(f"non-numeric {c}")
        elif (s <= 0).any():
            errs.append(f"non-positive {c}")
    if df.duplicated(subset=["portfolio_id", "transaction_id"]).any():
        errs.append("duplicate transaction_id")
    if not errs:  # running balance per portfolio+symbol must never go negative
        t = df.assign(date=parsed).sort_values("date", kind="stable")
        bal = {}
        for r in t.itertuples():
            key = (r.portfolio_id, r.symbol)
            bal[key] = bal.get(key, 0) + (r.quantity if r.transaction_type == "BUY" else -r.quantity)
            if bal[key] < 0:
                errs.append(f"oversell: {r.symbol}")
                break
    return errs
