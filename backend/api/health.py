"""GET /api/portfolio/health: the Portfolio Health Score (methodology health-v2)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from .. import schemas
from ..services import analysis_service

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/health", response_model=schemas.HealthScore)
def health(portfolio_id: Optional[str] = None):
    return analysis_service.analysis_for(portfolio_id)["health_score"]
