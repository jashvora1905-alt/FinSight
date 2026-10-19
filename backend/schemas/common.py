from __future__ import annotations

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


class UploadInputs(BaseModel):
    transactions_provided: bool
    price_history_provided: bool
