"""Portfolio analytics responses (analytics, Aditya) and the upload envelope."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .behavior import Behavior
from .common import UploadInputs
from .health import HealthScore
from .risk import Risk


class Mover(BaseModel):
    symbol: str
    return_pct: Optional[float] = None
    pnl: Optional[float] = None


class Summary(BaseModel):
    invested_value: Optional[float] = None
    current_value: Optional[float] = None
    pnl: Optional[float] = None
    return_pct: Optional[float] = None
    status: str
    number_of_holdings: int
    gainers: int
    losers: int
    unchanged: int
    total_gains: Optional[float] = None
    total_losses: Optional[float] = None
    top_gainers: List[Mover]
    top_losers: List[Mover]
    largest_pnl_contributor: Optional[Mover] = None
    largest_pnl_detractor: Optional[Mover] = None


class Holding(BaseModel):
    symbol: str
    company_name: str
    asset_type: str
    sector: str
    quantity: float
    average_buy_price: Optional[float] = None
    current_price: Optional[float] = None
    invested_value: Optional[float] = None
    current_value: Optional[float] = None
    pnl: Optional[float] = None
    return_pct: Optional[float] = None
    weight_pct: Optional[float] = None
    contribution_pct: Optional[float] = None
    status: str
    price_missing: bool


class AllocationRow(BaseModel):
    name: str
    current_value: Optional[float] = None
    invested_value: Optional[float] = None
    weight_pct: Optional[float] = None
    invested_weight_pct: Optional[float] = None
    drift_pct: Optional[float] = None
    pnl: Optional[float] = None
    return_pct: Optional[float] = None
    holdings: int


class Allocation(BaseModel):
    basis: str
    by_asset_type: List[AllocationRow]
    by_sector: List[AllocationRow]
    by_security: List[AllocationRow]
    number_of_asset_types: int
    number_of_sectors: int


class Analytics(BaseModel):
    portfolio_id: Optional[str] = None
    summary: Summary
    holdings: List[Holding]
    allocation: Allocation
    warnings: List[str]


class PerformanceHolding(BaseModel):
    symbol: str
    pnl: Optional[float] = None
    return_pct: Optional[float] = None
    contribution_pct: Optional[float] = None


class Performance(BaseModel):
    summary: Summary
    holdings: List[PerformanceHolding]


class UploadResponse(BaseModel):
    portfolio_id: Optional[str] = None   # null when the upload holds several portfolios analysed together
    portfolio_ids: List[str]
    inputs: UploadInputs
    analytics: Analytics
    risk: Risk
    behavior: Optional[Behavior] = None
    health_score: HealthScore
