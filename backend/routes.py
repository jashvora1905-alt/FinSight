from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from . import schemas, service, store
from .errors import ApiError

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # per file


@router.get("/health", response_model=schemas.HealthResponse, tags=["system"])
def health():
    return {"status": "ok"}


def _read_upload(file: Optional[UploadFile], field: str) -> Optional[str]:
    if file is None or not (file.filename or "").strip():
        return None
    if not file.filename.lower().endswith(".csv"):
        raise ApiError(415, f"The '{field}' file must be a .csv file.")
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ApiError(413, f"The '{field}' file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    return service.decode_csv(raw, field)


def _clean(value: Optional[str]) -> Optional[str]:
    value = value.strip() if value else None
    return value or None


@router.post("/api/upload", response_model=schemas.UploadResponse, tags=["upload"])
def upload(
    portfolio: UploadFile = File(..., description="Portfolio CSV (required)"),
    transactions: Optional[UploadFile] = File(None, description="Transactions CSV (optional)"),
    price_history: Optional[UploadFile] = File(None, description="Historical prices CSV: date,symbol,close (optional)"),
    portfolio_id: Optional[str] = Form(None, description="Analyse only this portfolio_id"),
    observation_start: Optional[str] = Form(None, description="Behaviour window start, YYYY-MM-DD"),
    observation_end: Optional[str] = Form(None, description="Behaviour window end, YYYY-MM-DD"),
):
    portfolio_text = _read_upload(portfolio, "portfolio")
    if portfolio_text is None:
        raise ApiError(422, "The 'portfolio' file is required.")
    candidate = store.Upload(
        id="",
        portfolio_csv=portfolio_text,
        transactions_csv=_read_upload(transactions, "transactions"),
        price_history_csv=_read_upload(price_history, "price_history"),
        portfolio_id=_clean(portfolio_id),
        observation_start=_clean(observation_start),
        observation_end=_clean(observation_end),
    )
    upload_id = store.make_upload_id(
        candidate.portfolio_csv, candidate.transactions_csv, candidate.price_history_csv,
        candidate.portfolio_id, candidate.observation_start, candidate.observation_end)
    saved = store.Upload(**{**candidate.__dict__, "id": upload_id})

    result = service.run_analysis(saved)  # validate + analyse first; bad uploads are never stored
    store.save_upload(saved)
    return {
        "upload_id": upload_id,
        "portfolio_id": result["analytics"]["portfolio_id"],
        "inputs": {"transactions_provided": saved.transactions_csv is not None,
                   "price_history_provided": saved.price_history_csv is not None},
        **result,
    }


def _analysis(upload_id: Optional[str]) -> dict:
    u = store.get_upload(upload_id)
    if u is None:
        if upload_id is None:
            raise ApiError(404, "No portfolio has been uploaded yet. POST /api/upload first.")
        raise ApiError(404, f"Upload '{upload_id}' not found.")
    return service.run_analysis(u)


_UPLOAD_ID = {"description": "Defaults to the most recent upload"}


@router.get("/api/portfolio/summary", response_model=schemas.Summary, tags=["portfolio"])
def portfolio_summary(upload_id: Optional[str] = None):
    return _analysis(upload_id)["analytics"]["summary"]


@router.get("/api/portfolio/holdings", response_model=list[schemas.Holding], tags=["portfolio"])
def portfolio_holdings(upload_id: Optional[str] = None):
    return _analysis(upload_id)["analytics"]["holdings"]


@router.get("/api/portfolio/performance", response_model=schemas.Performance, tags=["portfolio"])
def portfolio_performance(upload_id: Optional[str] = None):
    a = _analysis(upload_id)["analytics"]
    return {"summary": a["summary"], "holdings": a["holdings"]}


@router.get("/api/portfolio/allocation", response_model=schemas.Allocation, tags=["portfolio"])
def portfolio_allocation(upload_id: Optional[str] = None):
    return _analysis(upload_id)["analytics"]["allocation"]


@router.get("/api/portfolio/risk", response_model=schemas.Risk, tags=["portfolio"])
def portfolio_risk(upload_id: Optional[str] = None):
    return _analysis(upload_id)["risk"]


@router.get("/api/portfolio/health-score", response_model=schemas.HealthScore, tags=["portfolio"])
def portfolio_health_score(upload_id: Optional[str] = None):
    return _analysis(upload_id)["health_score"]


@router.get("/api/portfolio/behavior", response_model=schemas.Behavior, tags=["portfolio"])
def portfolio_behavior(upload_id: Optional[str] = None):
    behavior = _analysis(upload_id)["behavior"]
    if behavior is None:
        raise ApiError(404, "No transactions were uploaded with this portfolio.")
    return behavior
