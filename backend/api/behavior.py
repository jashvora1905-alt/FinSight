"""GET /api/portfolio/behavior."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from .. import schemas
from ..services import analysis_service
from ..services.errors import ApiError

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/behavior", response_model=schemas.Behavior)
def behavior(portfolio_id: Optional[str] = None):
    result = analysis_service.analysis_for(portfolio_id)["behavior"]
    if result is None:
        raise ApiError(404, "No transactions were uploaded with this portfolio.")
    return result
