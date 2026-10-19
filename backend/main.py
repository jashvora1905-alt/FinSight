"""FinSight FastAPI app. Run from the repository root:

    python -m uvicorn backend.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, schemas
from .api import behavior, health, insights, portfolio, risk
from .database import init_db
from .services.errors import ApiError

log = logging.getLogger("finsight.backend")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="FinSight API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


def _error(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


@app.exception_handler(ApiError)
async def _api_error(_: Request, exc: ApiError):
    return _error(exc.status_code, exc.detail)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    msgs = [f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()]
    return _error(422, "; ".join(msgs) or "Invalid request.")


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, str(exc.detail))


@app.exception_handler(Exception)
async def _unexpected(_: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return _error(500, "Internal server error.")


@app.get("/health", response_model=schemas.LivenessResponse, tags=["system"])
def liveness():
    """Service liveness probe. (The portfolio health score is GET /api/portfolio/health.)"""
    return {"status": "ok"}


for module in (portfolio, risk, behavior, health, insights):
    app.include_router(module.router)
