"""GET /api/portfolio/insights: AI Insight Engine (Rayyan). Not integrated yet."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from ..services.errors import ApiError

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/insights")
def insights(portfolio_id: Optional[str] = None):
    # Placeholder until the AI module is delivered and its interface is known.
    raise ApiError(501, "AI insights are not available yet: the AI module has not been integrated.")
