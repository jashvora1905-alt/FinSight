"""Maps test 'kinds' to the delivered modules. Everything is wired through tests/adapters.py.

Rules (no more silent green):
  * A module in DELIVERED must import and expose its functions -> otherwise the test FAILS.
  * Only modules in NOT_DELIVERED may skip, and every skip prints the reason (run `pytest -rs`).
    Currently none: the Health Score engine (backend/services/health_score.py, Jash) is delivered.
  * The FastAPI app is required too. In a checkout without the backend, set FINSIGHT_SKIP_API=1
    to skip API tests knowingly; the default is to fail.

Contract (verified against the delivered code, Oct 2026):
  analytics.analyze_portfolio(df)["summary"]            -> invested_value, current_value, pnl, return_pct
  risk_engine.calculate_concentration(df)               -> largest_holding_pct (0-100), holding_hhi, sector_weights_pct
  risk_engine.analyze_diversification(df)               -> diversification_score (0-100)
  behavior.analyze_behavior(df.to_dict("records"))      -> summary / frequency / holdings / behavior_score ...
  backend.services.health_score.calculate_health_score(portfolio_df, transactions_df=None)
      -> {score, score_basis, missing_components, coverage, components{performance,risk,diversification,behavior}, explanation}
Invalid input raises ValueError (PortfolioDataError subclasses it).
"""
import importlib
import os

import pytest

from tests import adapters

NOT_DELIVERED = set()   # the ONE place that lists modules allowed to skip (currently none)

ADAPTERS = {
    ("analytics", "summary"): adapters.summary,
    ("risk", "concentration"): adapters.concentration,
    ("risk", "sectors"): adapters.sectors,
    ("risk", "diversification"): adapters.diversification,
    ("behavior", "analyze"): adapters.analyze,
}

HEALTH_MODULE = "backend.services.health_score"
APP_CANDIDATES = [("backend.main", "app"), ("backend.app.main", "app"), ("main", "app")]


def resolve(kind, fn="summary"):
    if kind == "health_score":
        try:
            return importlib.import_module(HEALTH_MODULE).calculate_health_score
        except (ImportError, AttributeError) as exc:
            pytest.fail(f"Health Score engine not importable from {HEALTH_MODULE}: {exc}")
    if kind in NOT_DELIVERED:
        pytest.skip(f"NOT DELIVERED: {kind} module")
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
