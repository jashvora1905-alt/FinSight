"""SQLite connection + schema.

Tables follow the README "Database Structure" (users, portfolios, holdings, transactions). Documented additions:
  * portfolios.id is TEXT (the CSV portfolio_id such as "P001"); observation_start/observation_end hold the
    optional behaviour window.
  * transactions.transaction_id keeps the CSV transaction_id (Prisha's module requires it).
  * price_history (date, symbol, close) holds the optional historical prices that the risk engine needs for
    volatility and maximum drawdown; the README defines no CSV format for them.
"""
from __future__ import annotations

import sqlite3

from .. import config

_NOW = "strftime('%Y-%m-%d %H:%M:%f', 'now')"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT,
    email      TEXT,
    created_at TEXT NOT NULL DEFAULT ({_NOW})
);
CREATE TABLE IF NOT EXISTS portfolios (
    id                TEXT PRIMARY KEY,
    user_id           INTEGER REFERENCES users(id),
    name              TEXT,
    observation_start TEXT,
    observation_end   TEXT,
    created_at        TEXT NOT NULL DEFAULT ({_NOW})
);
CREATE TABLE IF NOT EXISTS holdings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id      TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol            TEXT,
    company_name      TEXT,
    asset_type        TEXT,
    sector            TEXT,
    quantity          REAL,
    average_buy_price REAL,
    current_price     REAL
);
CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id   TEXT,
    portfolio_id     TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    date             TEXT,
    symbol           TEXT,
    transaction_type TEXT,
    quantity         REAL,
    price            REAL
);
CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    date         TEXT,
    symbol       TEXT,
    close        REAL
);
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio      ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio  ON transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_price_history_portfolio ON price_history(portfolio_id);
"""


def connect() -> sqlite3.Connection:
    """Open the DB and make sure the tables exist, so nothing depends on app-startup order."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def init_db() -> None:
    """Eager creation at startup (connect() also guarantees the tables)."""
    connect().close()
