"""Pydantic response models. Field names follow the module methodology docs exactly
(analytics_methodology.md §5, risk_methodology.md, behavior_methodology.md)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ---------------- analytics (Aditya) ----------------


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


# ---------------- risk (Soumil) ----------------


class Concentration(BaseModel):
    largest_holding_pct: float
    top_3_holdings_pct: float
    holding_hhi: float
    largest_sector_pct: float
    sector_hhi: float
    holding_weights_pct: Dict[str, float]
    sector_weights_pct: Dict[str, float]


class Diversification(BaseModel):
    number_of_holdings: int
    number_of_sectors: int
    effective_holdings: float
    effective_sectors: float
    diversification_score: float
    diversification_level: str
    diversification_gaps: List[str]


class RiskScore(BaseModel):
    score: float
    level: str
    components: Dict[str, float]
    component_weights: Dict[str, float]
    methodology_version: str
    higher_score_means: str


class Risk(BaseModel):
    portfolio_id: Optional[str] = None
    concentration: Concentration
    diversification: Diversification
    risk_metrics: Dict[str, Any]  # shape depends on whether price history was supplied
    risk_score: RiskScore
    limitations: List[str]


# ---------------- behaviour (Prisha) ----------------


class Behavior(BaseModel):
    methodology_version: str
    portfolio_id: Optional[str] = None
    status: str
    summary: Dict[str, Any]
    frequency: Optional[Dict[str, Any]] = None
    holdings: Optional[Dict[str, Any]] = None
    panic_selling_indicator: Optional[Dict[str, Any]] = None
    behavior_score: Dict[str, Any]
    warnings: List[str]


# ---------------- health score (Jash) ----------------


class HealthComponent(BaseModel):
    value: Optional[float] = None
    weight_applied: float
    available: bool
    status: Optional[str] = None
    source: str


class HealthComponents(BaseModel):
    risk_diversification: HealthComponent
    behavior: HealthComponent


class HealthScore(BaseModel):
    score: float
    band: str
    score_basis: str  # "full" (risk + behaviour) or "risk_only" (behaviour unavailable -> provisional)
    coverage: float
    components: HealthComponents
    methodology_version: str


# ---------------- endpoint envelopes ----------------


class UploadInputs(BaseModel):
    transactions_provided: bool
    price_history_provided: bool


class UploadResponse(BaseModel):
    upload_id: str
    portfolio_id: Optional[str] = None
    inputs: UploadInputs
    analytics: Analytics
    risk: Risk
    behavior: Optional[Behavior] = None
    health_score: HealthScore


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str
