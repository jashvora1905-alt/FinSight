"""Reference tests for Aditya's analytics module (renamed to avoid clashing with his tests/test_analytics.py)."""
import pytest

from tests import adapters, oracle
from tests.contract import resolve

TOL = 0.01   # module rounds money and % to 2 dp


def test_summary_matches_oracle(portfolio):
    got, exp = resolve("analytics")(portfolio), oracle.summary(portfolio)
    for k, v in exp.items():
        assert got[k] == pytest.approx(v, abs=TOL), k


def test_pnl_is_value_minus_invested(portfolio):
    got = resolve("analytics")(portfolio)
    assert got["total_pnl"] == pytest.approx(got["current_value"] - got["total_invested"], abs=TOL)


def test_holding_contributions_add_up_to_portfolio_return(portfolio):
    r = adapters.analytics_raw(portfolio)
    assert sum(h["contribution_pct"] for h in r["holdings"]) == pytest.approx(r["summary"]["return_pct"], abs=0.1)


def test_single_holding(edge):
    df = edge("portfolio_single_holding")
    got = resolve("analytics")(df)
    assert got["current_value"] == pytest.approx(10 * 3650.25, abs=TOL)
    assert got["return_pct"] == pytest.approx(oracle.summary(df)["return_pct"], abs=TOL)


def test_all_losses_gives_negative_return(edge):
    got = resolve("analytics")(edge("portfolio_all_losses"))
    assert got["total_pnl"] < 0 and got["return_pct"] < 0


def test_deterministic_and_does_not_mutate_input(portfolio):
    before = portfolio.copy()
    f = resolve("analytics")
    assert f(portfolio) == f(portfolio)
    assert portfolio.equals(before)


@pytest.mark.parametrize("name", [
    "portfolio_empty", "portfolio_missing_column", "portfolio_invalid_values",
    "portfolio_negative_quantity", "portfolio_non_numeric_price",
    "portfolio_blank_symbol", "portfolio_zero_buy_price"])
def test_invalid_input_raises_value_error(edge, name):
    with pytest.raises(ValueError):
        resolve("analytics")(edge(name))


# ---- Decision tests: assert what the module DOES (see BUG_LOG B004-B006) ----

def test_duplicate_symbols_are_merged_with_warning(edge):
    r = adapters.analytics_raw(edge("portfolio_duplicates"))
    assert len(r["holdings"]) == 1
    h = r["holdings"][0]
    assert h["quantity"] == 15
    assert h["average_buy_price"] == pytest.approx((10 * 3300 + 5 * 3400) / 15, abs=TOL)
    assert any("Merged" in w for w in r["warnings"])


def test_zero_quantity_row_is_skipped_with_warning(edge):
    r = adapters.analytics_raw(edge("portfolio_zero_quantity"))
    assert [h["symbol"] for h in r["holdings"]] == ["TCS"]
    assert any("zero quantity" in w for w in r["warnings"])


def test_zero_current_price_falls_back_to_buy_price_and_is_flagged(edge):
    r = adapters.analytics_raw(edge("portfolio_zero_current_price"))
    tcs = next(h for h in r["holdings"] if h["symbol"] == "TCS")
    assert tcs["price_missing"] is True
    assert tcs["current_value"] == tcs["invested_value"]
    assert any("price missing" in w.lower() for w in r["warnings"])


def test_multi_portfolio_file_warns_unless_id_given(edge):
    df = edge("portfolio_multi_portfolio")
    assert any("several portfolios" in w for w in adapters.analytics_raw(df)["warnings"])
    only = adapters.analytics_raw(df, portfolio_id="P002")
    assert [h["symbol"] for h in only["holdings"]] == ["INFY"]
    with pytest.raises(ValueError):
        adapters.analytics_raw(df, portfolio_id="P999")
