import math

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


def test_poor_behaviour_does_not_raise_score(portfolio, transactions):
    """Dropping the clean trades and keeping only the loss-making PAYTM churn must not look healthier."""
    churn = transactions[transactions["symbol"] == "PAYTM"]
    assert _score(portfolio, churn) <= _score(portfolio, None) + 1e-9


@pytest.mark.parametrize("name", ["portfolio_empty", "portfolio_invalid_values"])
def test_invalid_input_raises(edge, name):
    with pytest.raises(ValueError):
        resolve("health_score", "score")(edge(name), None)
