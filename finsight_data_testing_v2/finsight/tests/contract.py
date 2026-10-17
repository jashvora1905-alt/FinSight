"""Maps test 'kinds' to the delivered modules. Everything is wired through tests/adapters.py.

Rules (no more silent green):
  * A module in DELIVERED must import and expose its functions -> otherwise the test FAILS.
  * Only modules in NOT_DELIVERED may skip, and every skip prints the reason (run `pytest -rs`).
    Currently only the Health Score engine (owner: Jash) is not delivered.
  * The FastAPI app is required too. In a checkout without the backend, set FINSIGHT_SKIP_API=1
    to skip API tests knowingly; the default is to fail.

Contract (verified against the delivered code, Oct 2026):
  analytics.analyze_portfolio(df)["summary"]            -> invested_value, current_value, pnl, return_pct
  risk_engine.calculate_concentration(df)               -> largest_holding_pct (0-100), holding_hhi, sector_weights_pct
  risk_engine.analyze_diversification(df)               -> diversification_score (0-100)
  behavior.analyze_behavior(df.to_dict("records"))      -> summary / frequency / holdings / behavior_score ...
  health_score.calculate_health_score(portfolio_df, transactions_df=None) -> {"score": 0-100}   (assumed)
Invalid input raises ValueError (PortfolioDataError subclasses it).
"""
import importlib
import os

import pytest

from tests import adapters

NOT_DELIVERED = {"health_score"}   # the ONE place that lists modules allowed to skip

ADAPTERS = {
    ("analytics", "summary"): adapters.summary,
    ("risk", "concentration"): adapters.concentration,
    ("risk", "sectors"): adapters.sectors,
    ("risk", "diversification"): adapters.diversification,
    ("behavior", "analyze"): adapters.analyze,
}

HEALTH_MODULES = ["backend.health_score", "backend.app.health_score", "health_score"]
HEALTH_FUNCTIONS = ["calculate_health_score", "health_score"]
APP_CANDIDATES = [("backend.main", "app"), ("backend.app.main", "app"), ("main", "app")]


def resolve(kind, fn="summary"):
    if kind in NOT_DELIVERED:
        for mod_name in HEALTH_MODULES:
            try:
                mod = importlib.import_module(mod_name)
            except ImportError:
                continue
            for n in HEALTH_FUNCTIONS:
                if hasattr(mod, n):
                    return getattr(mod, n)
        pytest.skip(f"NOT DELIVERED: {kind} module (owner: Jash)")
    try:
        return ADAPTERS[(kind, fn)]
    except KeyError:
        pytest.fail(f"no adapter registered for ({kind!r}, {fn!r}) in tests/contract.py")


def resolve_app():
    for mod_name, attr in APP_CANDIDATES:
        try:
            return getattr(importlib.import_module(mod_name), attr)
        except (ImportError, AttributeError):
            continue
    if os.environ.get("FINSIGHT_SKIP_API") == "1":
        pytest.skip("FINSIGHT_SKIP_API=1: backend not in this checkout")
    pytest.fail("FastAPI app not found; check APP_CANDIDATES in tests/contract.py "
                "(or set FINSIGHT_SKIP_API=1 to skip API tests knowingly)")
