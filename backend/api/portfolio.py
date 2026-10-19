"""POST /api/portfolio/upload and the portfolio analytics endpoints (README: API Structure)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from .. import config, schemas
from ..services import analysis_service, upload_service
from ..services.errors import ApiError

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

PORTFOLIO_ID = {"description": "Stored portfolio to analyse. Default: the portfolio(s) of the most recent upload."}


def _read_upload(file: Optional[UploadFile], field: str) -> Optional[str]:
    if file is None or not (file.filename or "").strip():
        return None
    if not file.filename.lower().endswith(".csv"):
        raise ApiError(415, f"The '{field}' file must be a .csv file.")
    raw = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise ApiError(413, f"The '{field}' file is larger than {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    return upload_service.decode_csv(raw, field)


def _clean(value: Optional[str]) -> Optional[str]:
    value = value.strip() if value else None
    return value or None


@router.post("/upload", response_model=schemas.UploadResponse, tags=["upload"])
def upload(
    portfolio: UploadFile = File(..., description="Portfolio CSV (required)"),
    transactions: Optional[UploadFile] = File(None, description="Transactions CSV (optional)"),
    price_history: Optional[UploadFile] = File(None, description="Historical prices CSV: date,symbol,close (optional)"),
    portfolio_id: Optional[str] = Form(None, description="Analyse and store only this portfolio_id"),
    observation_start: Optional[str] = Form(None, description="Behaviour window start, YYYY-MM-DD"),
    observation_end: Optional[str] = Form(None, description="Behaviour window end, YYYY-MM-DD"),
):
    portfolio_text = _read_upload(portfolio, "portfolio")
    if portfolio_text is None:
        raise ApiError(422, "The 'portfolio' file is required.")
    return upload_service.process_upload(
        portfolio_text, _read_upload(transactions, "transactions"), _read_upload(price_history, "price_history"),
        _clean(portfolio_id), _clean(observation_start), _clean(observation_end))


@router.get("/summary", response_model=schemas.Summary)
def summary(portfolio_id: Optional[str] = None):
    return analysis_service.analysis_for(portfolio_id)["analytics"]["summary"]


@router.get("/holdings", response_model=list[schemas.Holding])
def holdings(portfolio_id: Optional[str] = None):
    return analysis_service.analysis_for(portfolio_id)["analytics"]["holdings"]


@router.get("/performance", response_model=schemas.Performance)
def performance(portfolio_id: Optional[str] = None):
    a = analysis_service.analysis_for(portfolio_id)["analytics"]
    return {"summary": a["summary"], "holdings": a["holdings"]}


@router.get("/allocation", response_model=schemas.Allocation)
def allocation(portfolio_id: Optional[str] = None):
    return analysis_service.analysis_for(portfolio_id)["analytics"]["allocation"]
