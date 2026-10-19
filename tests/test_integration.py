"""Roadmap step 5: data flows CSV -> analytics -> risk -> behaviour (-> health score once delivered)."""
import pytest

from analytics import compute_holdings, load_portfolio
from analytics import portfolio_metrics
from behavior import transaction_analysis
from tests import adapters, oracle
from tests.contract import resolve
from tests.validators import PORTFOLIO_COLUMNS, TRANSACTION_COLUMNS, validate_portfolio, validate_transactions


def test_our_schema_matches_what_the_modules_require():
    """Guards against the original B001 drift: if a module changes its columns, this fails first."""
    assert list(portfolio_metrics.REQUIRED_COLUMNS) == PORTFOLIO_COLUMNS
    assert set(transaction_analysis.REQUIRED_FIELDS) == set(TRANSACTION_COLUMNS)


def test_pipeline_on_sample_data(portfolio, transactions):
    assert validate_portfolio(portfolio) == [] and validate_transactions(transactions) == []
    summary = resolve("analytics")(portfolio)
    conc = resolve("risk", "concentration")(portfolio)
    div = resolve("risk", "diversification")(portfolio)
    behav = resolve("behavior", "analyze")(transactions)
    assert summary["current_value"] > 0
    assert 0 < conc["hhi"] <= 1 and 0 <= div <= 100
    assert behav["total_trades"] == len(transactions)


def test_analytics_and_risk_agree_on_weights(portfolio):
    holdings = adapters.analytics_raw(portfolio)["holdings"]
    risk = adapters.concentration_raw(portfolio)["holding_weights_pct"]
    for h in holdings:
        assert risk[h["symbol"]] == pytest.approx(h["weight_pct"], abs=0.01), h["symbol"]


def test_risk_accepts_analytics_cleaned_holdings(portfolio):
    cleaned = compute_holdings(load_portfolio(portfolio)[0])
    assert adapters.diversification_raw(cleaned)["number_of_holdings"] == len(portfolio)


def test_behavior_and_portfolio_describe_the_same_account(portfolio, transactions):
    assert adapters.behavior_raw(transactions)["portfolio_id"] == adapters.analytics_raw(portfolio)["portfolio_id"]
    assert oracle.net_positions(transactions) == dict(zip(portfolio["symbol"], portfolio["quantity"]))


def test_pipeline_is_repeatable(portfolio, transactions):
    run = lambda: (resolve("analytics")(portfolio), resolve("risk", "concentration")(portfolio),
                   resolve("behavior", "analyze")(transactions))
    assert run() == run()


@pytest.mark.parametrize("name", ["portfolio_single_holding", "portfolio_concentrated", "portfolio_all_losses",
                                  "portfolio_duplicates", "portfolio_zero_quantity", "portfolio_zero_current_price"])
def test_pipeline_survives_edge_portfolios(edge, name):
    df = edge(name)
    resolve("analytics")(df)
    resolve("risk", "concentration")(df)
    resolve("risk", "diversification")(df)


# Health Score is delivered (backend/services/health_score.py): a missing module now FAILS.
def test_health_score_end_to_end(portfolio, transactions):
    health = resolve("health_score", "score")(portfolio, transactions)
    assert 0 <= health["score"] <= 100
