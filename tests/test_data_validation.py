"""Roadmap steps 1-2: datasets exist, follow the shared schema, and edge cases behave as designed."""
import pytest

from tests import oracle
from tests.validators import (PORTFOLIO_COLUMNS, TRANSACTION_COLUMNS, check_asset_types,
                              validate_portfolio, validate_transactions)

STRICT_INVALID_PORTFOLIOS = {
    "portfolio_empty": "no rows",
    "portfolio_missing_column": "missing columns",
    "portfolio_duplicates": "duplicate symbols",
    "portfolio_zero_quantity": "non-positive quantity",
    "portfolio_zero_current_price": "non-positive current_price",
    "portfolio_negative_quantity": "non-positive quantity",
    "portfolio_non_numeric_price": "non-numeric current_price",
    "portfolio_blank_symbol": "blank symbol",
    "portfolio_zero_buy_price": "non-positive average_buy_price",
}


def test_sample_portfolio_is_valid(portfolio):
    assert validate_portfolio(portfolio) == []
    assert check_asset_types(portfolio) == []
    assert len(portfolio) >= 10


def test_sample_files_use_exactly_the_shared_columns(portfolio, transactions):
    assert list(portfolio.columns) == PORTFOLIO_COLUMNS
    assert list(transactions.columns) == TRANSACTION_COLUMNS      # no fees column


def test_sample_portfolio_has_variety(portfolio):
    assert portfolio["sector"].nunique() >= 6
    assert {"Equity", "ETF", "Mutual Fund"} <= set(portfolio["asset_type"])
    pnl = oracle.enrich(portfolio)["pnl"]
    assert (pnl > 0).any() and (pnl < 0).any(), "need both gainers and a loser"


def test_sample_transactions_are_valid(transactions):
    assert validate_transactions(transactions) == []


def test_single_portfolio_id_across_both_files(portfolio, transactions):
    assert set(portfolio["portfolio_id"]) == set(transactions["portfolio_id"]) == {"P001"}


def test_transactions_reconcile_with_portfolio(portfolio, transactions):
    """Net BUY-SELL per symbol must equal portfolio quantity."""
    assert oracle.net_positions(transactions) == dict(zip(portfolio["symbol"], portfolio["quantity"]))


@pytest.mark.parametrize("name,expected", STRICT_INVALID_PORTFOLIOS.items())
def test_strict_validator_rejects_edge_portfolios(edge, name, expected):
    assert any(expected in e for e in validate_portfolio(edge(name))), name


def test_invalid_values_file_reports_every_problem(edge):
    errs = " | ".join(validate_portfolio(edge("portfolio_invalid_values")))
    assert "blank symbol" in errs and "non-numeric average_buy_price" in errs


@pytest.mark.parametrize("name", ["portfolio_single_holding", "portfolio_concentrated",
                                  "portfolio_all_losses", "portfolio_multi_portfolio"])
def test_valid_edge_portfolios_pass(edge, name):
    assert validate_portfolio(edge(name)) == []


@pytest.mark.parametrize("name,expected", [
    ("transactions_empty", "no rows"),
    ("transactions_invalid", "invalid transaction_type"),
    ("transactions_oversell", "oversell"),
])
def test_strict_validator_rejects_edge_transactions(edge, name, expected):
    assert any(expected in e for e in validate_transactions(edge(name))), name


def test_invalid_transactions_report_date(edge):
    assert any("invalid date" in e for e in validate_transactions(edge("transactions_invalid")) + 
               validate_transactions(edge("transactions_invalid").assign(transaction_type="BUY")))


@pytest.mark.parametrize("name", ["transactions_multi_portfolio", "transactions_short_history",
                                  "transactions_overtrading"])
def test_valid_edge_transactions_pass(edge, name):
    assert validate_transactions(edge(name)) == []
