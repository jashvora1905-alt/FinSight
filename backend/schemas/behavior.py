"""Behaviour response (behavior, Prisha)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
