"""GET /api/portfolio/risk and /api/portfolio/diversification."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from .. import schemas
from ..services import analysis_service

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/risk", response_model=schemas.Risk)
def risk(portfolio_id: Optional[str] = None):
    return analysis_service.analysis_for(portfolio_id)["risk"]


@router.get("/diversification", response_model=schemas.Diversification)
def diversification(portfolio_id: Optional[str] = None):
    return analysis_service.analysis_for(portfolio_id)["risk"]["diversification"]
