import math

import pandas as pd
import pytest

from tests.contract import resolve


def _score(portfolio, tx=None):
    return resolve("health_score", "score")(portfolio, tx)["score"]


def test_score_in_range_and_finite(portfolio, transactions):
    s = _score(portfolio, transactions)
    assert 0 <= s <= 100 and math.isfinite(s)


def test_deterministic(portfolio, transactions):
    assert _score(portfolio, transactions) == _score(portfolio, transactions)


def test_works_without_transactions(portfolio):
    assert 0 <= _score(portfolio, None) <= 100


def test_diversified_scores_higher_than_concentrated(portfolio, edge):
    assert _score(portfolio) > _score(edge("portfolio_concentrated"))


def test_single_holding_scores_below_sample(portfolio, edge):
    assert _score(edge("portfolio_single_holding")) < _score(portfolio)


def _history(loss_making):
    """>= 30 days and >= 10 transactions so the behaviour score is available.
    loss_making -> every sale is a short-hold loss of 8%; otherwise the sales are profitable
    and held for weeks."""
    rows, start = [], pd.Timestamp("2026-01-01")
    for k in range(6):
        buy = start + pd.Timedelta(days=k * 6)
        sell = buy + pd.Timedelta(days=2 if loss_making else 40)
        rows.append((f"B{k}", "P001", str(buy.date()), "TCS", "BUY", 10, 100))
        rows.append((f"S{k}", "P001", str(sell.date()), "TCS", "SELL", 10, 92 if loss_making else 130))
    return pd.DataFrame(rows, columns=["transaction_id", "portfolio_id", "date", "symbol",
                                       "transaction_type", "quantity", "price"])


def test_poor_behaviour_scores_below_good_behaviour_on_the_same_portfolio(portfolio):
    good = resolve("health_score", "score")(portfolio, _history(False))
    poor = resolve("health_score", "score")(portfolio, _history(True))
    assert poor["components"]["behavior"]["available"] and good["components"]["behavior"]["available"]
    assert poor["score"] < good["score"]


def test_without_transactions_the_score_is_provisional(portfolio):
    r = resolve("health_score", "score")(portfolio, None)
    assert r["score_basis"] == "partial" and r["missing_components"] == ["behavior"] and r["coverage"] < 1


def test_all_four_readme_dimensions_are_reported(portfolio, transactions):
    r = resolve("health_score", "score")(portfolio, transactions)
    assert set(r["components"]) == {"performance", "risk", "diversification", "behavior"}
    assert r["explanation"]["summary"] and r["explanation"]["drivers"]


# ---- sign-off checks for docs/health_score_methodology.md section 4 (validation on our data) ----
PORTFOLIOS = ["portfolio_concentrated", "portfolio_single_holding"]


@pytest.mark.parametrize("case", ["none", "poor", "sample", "good"])
def test_portfolio_ordering_holds_for_every_behaviour_case(portfolio, edge, transactions, case):
    tx = {"none": None, "poor": _history(True), "sample": transactions, "good": _history(False)}[case]
    f = resolve("health_score", "score")
    sample, conc, single = (f(df, tx)["score"] for df in
                            (portfolio, edge("portfolio_concentrated"), edge("portfolio_single_holding")))
    assert sample > conc > single


@pytest.mark.parametrize("name", [None, "portfolio_all_losses", "portfolio_concentrated", "portfolio_single_holding"])
def test_behaviour_ordering_poor_below_sample_below_good(portfolio, edge, transactions, name):
    df = portfolio if name is None else edge(name)
    f = resolve("health_score", "score")
    poor, mid, good = (f(df, tx)["score"] for tx in (_history(True), transactions, _history(False)))
    assert poor < mid < good


def test_documented_sample_scores(portfolio, transactions):
    """Pins the numbers quoted in the methodology doc; fails if weights or scales change without the doc."""
    f = resolve("health_score", "score")
    assert f(portfolio, None)["score"] == pytest.approx(69.49, abs=0.01)
    assert f(portfolio, transactions)["score"] == pytest.approx(72.43, abs=0.01)


@pytest.mark.parametrize("name", ["portfolio_empty", "portfolio_invalid_values"])
def test_invalid_input_raises(edge, name):
    with pytest.raises(ValueError):
        resolve("health_score", "score")(edge(name), None)
