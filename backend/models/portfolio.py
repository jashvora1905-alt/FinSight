"""Row models for the SQLite tables (README: Database Structure). Plain dataclasses, no ORM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Portfolio:
    id: str                                  # the portfolio_id used in the CSV files, e.g. "P001"
    name: Optional[str] = None
    user_id: Optional[int] = None            # users are not implemented in the prototype (no login)
    observation_start: Optional[str] = None  # optional behaviour-analysis window, YYYY-MM-DD
    observation_end: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Holding:
    portfolio_id: str
    symbol: Optional[str]
    company_name: Optional[str]
    asset_type: Optional[str]
    sector: Optional[str]
    quantity: Optional[float]
    average_buy_price: Optional[float]
    current_price: Optional[float]
    id: Optional[int] = None


@dataclass
class Transaction:
    portfolio_id: str
    transaction_id: Optional[str]
    date: Optional[str]
    symbol: Optional[str]
    transaction_type: Optional[str]
    quantity: Optional[float]
    price: Optional[float]
    id: Optional[int] = None


@dataclass
class PricePoint:
    portfolio_id: str
    date: Optional[str]
    symbol: Optional[str]
    close: Optional[float]
    id: Optional[int] = None
