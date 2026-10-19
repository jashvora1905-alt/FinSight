"""Risk & diversification responses (risk_engine, Soumil)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
