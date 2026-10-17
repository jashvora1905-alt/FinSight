"""Minimal SQLite persistence: keeps the raw uploaded CSVs so the GET endpoints can
re-run the (deterministic) analysis modules on them. Nothing is calculated here.

DB file: $FINSIGHT_DB, default backend/finsight.db.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path(os.environ.get("FINSIGHT_DB", Path(__file__).resolve().parent / "finsight.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    id                TEXT PRIMARY KEY,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    portfolio_csv     TEXT NOT NULL,
    transactions_csv  TEXT,
    price_history_csv TEXT,
    portfolio_id      TEXT,
    observation_start TEXT,
    observation_end   TEXT
)
"""


@dataclass(frozen=True)
class Upload:
    id: str
    portfolio_csv: str
    transactions_csv: Optional[str]
    price_history_csv: Optional[str]
    portfolio_id: Optional[str]
    observation_start: Optional[str]
    observation_end: Optional[str]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(_SCHEMA)


def make_upload_id(*parts: Optional[str]) -> str:
    """Content hash: the same inputs always give the same id (deterministic API output)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(b"\x00" if p is None else b"\x01" + p.encode("utf-8"))
        h.update(b"\xff")
    return h.hexdigest()[:16]


def save_upload(u: Upload) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            """INSERT INTO uploads (id, portfolio_csv, transactions_csv, price_history_csv,
                                    portfolio_id, observation_start, observation_end)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET created_at = strftime('%Y-%m-%d %H:%M:%f', 'now')""",
            (u.id, u.portfolio_csv, u.transactions_csv, u.price_history_csv,
             u.portfolio_id, u.observation_start, u.observation_end),
        )


def get_upload(upload_id: Optional[str]) -> Optional[Upload]:
    """The upload with this id, or the most recent one when upload_id is None."""
    with closing(_connect()) as conn:
        if upload_id is None:
            row = conn.execute(
                "SELECT * FROM uploads ORDER BY created_at DESC, rowid DESC LIMIT 1").fetchone()
        else:
            row = conn.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
    if row is None:
        return None
    return Upload(**{k: row[k] for k in Upload.__dataclass_fields__})
