"""
Portfolio metrics: loading and validating portfolio data, building the
holding-level table, and the single entry point `analyze_portfolio()`.

Input schema (Project Guide §18, Portfolio CSV):
    portfolio_id, symbol, company_name, asset_type, sector,
    quantity, average_buy_price, current_price
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .allocation import allocation_summary
from .calculations import absolute_pnl, current_value, invested_value, return_pct
from .performance import holding_performance, portfolio_performance

REQUIRED_COLUMNS = [
    "portfolio_id",
    "symbol",
    "company_name",
    "asset_type",
    "sector",
    "quantity",
    "average_buy_price",
    "current_price",
]
TEXT_DEFAULTS = {"company_name": None, "asset_type": "Unknown", "sector": "Unknown"}


class PortfolioDataError(ValueError):
    """Raised when portfolio data cannot be analysed."""


# ---------------------------------------------------------------------------
# Loading & validation
# ---------------------------------------------------------------------------

def load_portfolio(source) -> tuple[pd.DataFrame, list[str]]:
    """Load from a CSV path, file-like object or DataFrame, then validate."""
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        try:
            df = pd.read_csv(source)
        except pd.errors.EmptyDataError as exc:
            raise PortfolioDataError("Portfolio file is empty.") from exc
    return validate_portfolio(df)


def validate_portfolio(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Clean and validate portfolio rows.

    Rules (documented in docs/analytics_methodology.md):
    - all required columns must exist, otherwise PortfolioDataError
    - symbol is upper-cased; blank text fields get a default
    - quantity / prices must be numeric; negative values -> error
    - quantity == 0  -> row dropped with a warning
    - missing/zero average_buy_price -> error (invested value unknown)
    - missing/zero current_price -> average_buy_price used, row flagged, warning
    - duplicate symbols in one portfolio -> merged (quantity summed,
      buy price quantity-weighted)

    Returns (clean_df, warnings).
    """
    warnings: list[str] = []
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise PortfolioDataError(f"Missing required columns: {missing}")

    df = df[REQUIRED_COLUMNS].dropna(how="all")
    if df.empty:
        raise PortfolioDataError("Portfolio has no holdings.")

    df["portfolio_id"] = df["portfolio_id"].astype(str).str.strip()
    df["symbol"] = df["symbol"].fillna("").astype(str).str.strip().str.upper()
    if (df["symbol"].isin(["", "NAN"])).any():
        raise PortfolioDataError("Every holding must have a symbol.")

    for col, default in TEXT_DEFAULTS.items():
        df[col] = df[col].astype("string").str.strip()
        fill = df["symbol"] if default is None else default
        df[col] = df[col].mask(df[col].isna() | (df[col] == ""), fill)
        df[col] = df[col].astype(str)

    for col in ["quantity", "average_buy_price", "current_price"]:
        raw = df[col]
        df[col] = pd.to_numeric(raw, errors="coerce")
        bad = raw.notna() & df[col].isna()
        if bad.any():
            raise PortfolioDataError(
                f"Non-numeric {col} for: {df.loc[bad, 'symbol'].tolist()}"
            )
        if (df[col] < 0).any():
            raise PortfolioDataError(
                f"Negative {col} for: {df.loc[df[col] < 0, 'symbol'].tolist()}"
            )

    if df["quantity"].isna().any():
        raise PortfolioDataError(
            f"Missing quantity for: {df.loc[df['quantity'].isna(), 'symbol'].tolist()}"
        )
    zero_qty = df["quantity"] == 0
    if zero_qty.any():
        warnings.append(
            f"Skipped holdings with zero quantity: {df.loc[zero_qty, 'symbol'].tolist()}"
        )
        df = df[~zero_qty]
        if df.empty:
            raise PortfolioDataError("All holdings have zero quantity.")

    no_cost = df["average_buy_price"].isna() | (df["average_buy_price"] == 0)
    if no_cost.any():
        raise PortfolioDataError(
            "Missing average_buy_price for: " + str(df.loc[no_cost, "symbol"].tolist())
        )

    no_price = df["current_price"].isna() | (df["current_price"] == 0)
    df["price_missing"] = no_price
    if no_price.any():
        warnings.append(
            "Current price missing for "
            f"{df.loc[no_price, 'symbol'].tolist()}; average buy price used instead."
        )
        df.loc[no_price, "current_price"] = df.loc[no_price, "average_buy_price"]

    df = _merge_duplicates(df, warnings)
    return df.reset_index(drop=True), warnings


def _merge_duplicates(df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
    dup = df.duplicated(subset=["portfolio_id", "symbol"], keep=False)
    if not dup.any():
        return df
    warnings.append(
        f"Merged duplicate rows for: {sorted(df.loc[dup, 'symbol'].unique().tolist())}"
    )
    df = df.assign(_cost=df["quantity"] * df["average_buy_price"])
    merged = df.groupby(["portfolio_id", "symbol"], sort=False, as_index=False).agg(
        company_name=("company_name", "first"),
        asset_type=("asset_type", "first"),
        sector=("sector", "first"),
        quantity=("quantity", "sum"),
        _cost=("_cost", "sum"),
        current_price=("current_price", "last"),
        price_missing=("price_missing", "any"),
    )
    merged["average_buy_price"] = merged["_cost"] / merged["quantity"]
    return merged.drop(columns="_cost")[REQUIRED_COLUMNS + ["price_missing"]]


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def compute_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Add invested value, current value, P&L, return % and weight to every holding."""
    out = df.copy()
    out["invested_value"] = invested_value(out["quantity"], out["average_buy_price"])
    out["current_value"] = current_value(out["quantity"], out["current_price"])
    out["pnl"] = absolute_pnl(out["current_value"], out["invested_value"])
    out["return_pct"] = return_pct(out["current_value"], out["invested_value"])
    total_current = out["current_value"].sum()
    out["weight_pct"] = out["current_value"] / total_current * 100 if total_current else 0.0
    return out


def portfolio_totals(holdings: pd.DataFrame) -> dict:
    """Portfolio-level invested value, current value, P&L and return."""
    invested = float(holdings["invested_value"].sum())
    current = float(holdings["current_value"].sum())
    return {
        "invested_value": invested,
        "current_value": current,
        "pnl": absolute_pnl(current, invested),
        "return_pct": return_pct(current, invested),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_portfolio(source, portfolio_id: Optional[str] = None) -> dict:
    """
    Run the full portfolio analytics and return one JSON-serialisable dict.

    Parameters
    ----------
    source       : CSV path, file-like object or DataFrame (Portfolio CSV schema)
    portfolio_id : optional filter when the file holds several portfolios
    """
    df, warnings = load_portfolio(source)

    if portfolio_id is not None:
        df = df[df["portfolio_id"] == str(portfolio_id)].reset_index(drop=True)
        if df.empty:
            raise PortfolioDataError(f"No holdings found for portfolio_id '{portfolio_id}'.")
    elif df["portfolio_id"].nunique() > 1:
        warnings.append(
            "File contains several portfolios; they were analysed together. "
            "Pass portfolio_id to analyse one."
        )

    holdings = compute_holdings(df)
    totals = portfolio_totals(holdings)

    return {
        "portfolio_id": portfolio_id if portfolio_id is not None
        else (df["portfolio_id"].iloc[0] if df["portfolio_id"].nunique() == 1 else None),
        "summary": portfolio_performance(holdings, totals),
        "holdings": holding_performance(holdings),
        "allocation": allocation_summary(holdings),
        "warnings": warnings,
    }
