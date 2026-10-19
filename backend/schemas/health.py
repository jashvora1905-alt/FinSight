"""Health Score response (health-v2, backend/services/health_score.py)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class HealthComponent(BaseModel):
    label: str
    value: Optional[float] = None
    base_weight: float
    weight_applied: float
    available: bool
    status: Optional[str] = None
    contribution_points: Optional[float] = None
    points_lost: Optional[float] = None
    source: str


class HealthComponents(BaseModel):
    performance: HealthComponent
    risk: HealthComponent
    diversification: HealthComponent
    behavior: HealthComponent


class Driver(BaseModel):
    component: str
    label: str
    value: float
    weight_applied: float
    points_lost: float


class Explanation(BaseModel):
    summary: str
    drivers: List[Driver]   # components that can still lose points, largest first
    notes: List[str]        # provisional-score and data-quality notes, plus module gaps passed through


class HealthScore(BaseModel):
    score: float
    band: str                       # Strong | Moderate | Weak | Poor
    score_basis: str                # "full" (all four scored) or "partial" (provisional)
    coverage: float                 # share of the full model's weight that was scored
    missing_components: List[str]
    components: HealthComponents
    explanation: Explanation
    methodology_version: str
