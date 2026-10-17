"""Reference tests for Soumil's risk_engine (renamed to avoid clashing with his tests/test_risk.py)."""
import pytest

from tests import adapters, oracle
from tests.contract import resolve


def test_concentration_matches_oracle(portfolio):
    got = resolve("risk", "concentration")(portfolio)
    assert got["top_holding_weight"] == pytest.approx(oracle.top_weight(portfolio), abs=1e-4)
    assert got["hhi"] == pytest.approx(oracle.hhi(portfolio), abs=1e-5)


def test_single_holding_is_fully_concentrated(edge):
    got = resolve("risk", "concentration")(edge("portfolio_single_holding"))
    assert got["top_holding_weight"] == pytest.approx(1.0)
    assert got["hhi"] == pytest.approx(1.0)


def test_sector_allocation_matches_oracle_and_sums_to_one(portfolio):
    got = resolve("risk", "sectors")(portfolio)
    assert sum(got.values()) == pytest.approx(1.0, abs=0.01)
    for sector, w in oracle.sector_weights(portfolio).items():
        assert got[sector] == pytest.approx(w, abs=1e-4)


def test_diversification_score_in_range(portfolio):
    assert 0 <= resolve("risk", "diversification")(portfolio) <= 100


def test_diversified_beats_concentrated(portfolio, edge):
    f = resolve("risk", "diversification")
    assert f(portfolio) > f(edge("portfolio_concentrated")) > f(edge("portfolio_single_holding"))


def test_single_holding_score_follows_documented_formula(edge):
    # 1/10 of the holdings credit (3) + 1/5 of the sector credit (5) + zero concentration credit
    assert resolve("risk", "diversification")(edge("portfolio_single_holding")) == pytest.approx(8.0)


def test_concentrated_portfolio_reports_gaps(edge):
    gaps = adapters.diversification_raw(edge("portfolio_concentrated"))["diversification_gaps"]
    assert any("single holding exceeds 35%" in g for g in gaps)


@pytest.mark.parametrize("name", ["portfolio_empty", "portfolio_missing_column",
                                  "portfolio_negative_quantity", "portfolio_non_numeric_price"])
def test_invalid_input_raises_value_error(edge, name):
    with pytest.raises(ValueError):
        resolve("risk", "concentration")(edge(name))


def test_works_on_cleaned_holdings_from_analytics(portfolio):
    """Risk should give the same answer on raw rows and on analytics' cleaned holdings table."""
    from analytics import compute_holdings, load_portfolio
    cleaned = compute_holdings(load_portfolio(portfolio)[0])
    assert adapters.concentration_raw(cleaned) == adapters.concentration_raw(portfolio)
