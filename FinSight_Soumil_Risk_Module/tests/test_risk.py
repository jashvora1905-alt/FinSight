import numpy as np
import pandas as pd
import pytest

from risk_engine.concentration import calculate_concentration
from risk_engine.diversification import analyze_diversification
from risk_engine.risk_metrics import calculate_historical_risk
from risk_engine.risk_score import analyze_portfolio_risk, calculate_risk_score


@pytest.fixture
def holdings():
    return pd.DataFrame(
        [
            ["P001", "RELIANCE", "Reliance Industries", "Equity", "Energy", 10, 2400, 2650],
            ["P001", "TCS", "Tata Consultancy Services", "Equity", "IT", 5, 3500, 4100],
            ["P001", "INFY", "Infosys", "Equity", "IT", 8, 1500, 1650],
            ["P001", "HDFCBANK", "HDFC Bank", "Equity", "Finance", 12, 1500, 1700],
            ["P001", "SUNPHARMA", "Sun Pharma", "Equity", "Healthcare", 7, 1400, 1600],
        ],
        columns=[
            "portfolio_id", "symbol", "company_name", "asset_type", "sector",
            "quantity", "average_buy_price", "current_price",
        ],
    )


@pytest.fixture
def price_history():
    dates = pd.date_range("2026-01-01", periods=40, freq="B")
    base = {
        "RELIANCE": 2400,
        "TCS": 3600,
        "INFY": 1500,
        "HDFCBANK": 1550,
        "SUNPHARMA": 1450,
    }
    rows = []
    for i, date in enumerate(dates):
        for j, (symbol, start) in enumerate(base.items()):
            # Deterministic, non-flat series with small symbol-specific oscillation.
            close = start * (1 + 0.0015 * i + 0.004 * np.sin((i + j) / 3.0))
            rows.append([date, symbol, close])
    return pd.DataFrame(rows, columns=["date", "symbol", "close"])


def test_concentration_weights_sum_to_100(holdings):
    result = calculate_concentration(holdings)
    assert sum(result["holding_weights_pct"].values()) == pytest.approx(100, abs=0.05)
    assert sum(result["sector_weights_pct"].values()) == pytest.approx(100, abs=0.05)
    assert 0 < result["holding_hhi"] <= 1
    assert 0 < result["sector_hhi"] <= 1


def test_diversification_output(holdings):
    result = analyze_diversification(holdings)
    assert result["number_of_holdings"] == 5
    assert result["number_of_sectors"] == 4
    assert 0 <= result["diversification_score"] <= 100
    assert result["diversification_level"] in {"Very Low", "Low", "Moderate", "High"}


def test_historical_metrics_available(holdings, price_history):
    result = calculate_historical_risk(holdings, price_history)
    assert result["historical_data_available"] is True
    assert result["annualized_volatility_pct"] >= 0
    assert result["maximum_drawdown_pct"] <= 0
    assert sum(result["risk_contribution_pct"].values()) == pytest.approx(100, abs=0.2)


def test_historical_metrics_graceful_when_missing(holdings):
    result = calculate_historical_risk(holdings, None)
    assert result["historical_data_available"] is False
    assert result["annualized_volatility_pct"] is None
    assert result["maximum_drawdown_pct"] is None


def test_risk_score_is_bounded(holdings, price_history):
    result = calculate_risk_score(holdings, price_history)
    assert 0 <= result["score"] <= 100
    assert result["level"] in {"Low", "Moderate", "High", "Very High"}


def test_main_structured_output(holdings, price_history):
    result = analyze_portfolio_risk(holdings, price_history)
    assert result["portfolio_id"] == "P001"
    assert set(result) == {
        "portfolio_id", "concentration", "diversification", "risk_metrics",
        "risk_score", "limitations",
    }


def test_single_stock_portfolio_is_highly_concentrated():
    df = pd.DataFrame(
        [{"symbol": "ABC", "sector": "IT", "quantity": 10, "current_price": 100}]
    )
    concentration = calculate_concentration(df)
    assert concentration["largest_holding_pct"] == 100.0
    assert concentration["largest_sector_pct"] == 100.0
    assert concentration["holding_hhi"] == 1.0


def test_missing_required_column_raises():
    df = pd.DataFrame([{"symbol": "ABC", "quantity": 1, "current_price": 100}])
    with pytest.raises(ValueError):
        calculate_concentration(df)
