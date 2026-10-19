"""
Tests for the Portfolio Analytics module (analytics/).

Expected values are worked out by hand in docs/analytics_methodology.md §6.
Run from the project root:  python -m pytest tests/test_analytics.py -v
"""

import io
import json
from pathlib import Path

import pandas as pd
import pytest

from analytics import (
    PortfolioDataError,
    absolute_pnl,
    analyze_portfolio,
    current_value,
    invested_value,
    load_portfolio,
    return_pct,
)

FIXTURE = Path(__file__).parent / "fixtures" / "analytics_portfolio.csv"
HEADER = ("portfolio_id,symbol,company_name,asset_type,sector,"
          "quantity,average_buy_price,current_price\n")


def csv(rows: str) -> io.StringIO:
    return io.StringIO(HEADER + rows)


# ---------------------------------------------------------------------------
# Basic formulas
# ---------------------------------------------------------------------------

def test_basic_formulas():
    assert invested_value(10, 2400) == 24000
    assert current_value(10, 2650) == 26500
    assert absolute_pnl(26500, 24000) == 2500
    assert return_pct(26500, 24000) == pytest.approx(10.41667, rel=1e-4)
    assert return_pct(0, 0) is None


def test_return_pct_series_handles_zero():
    r = return_pct(pd.Series([110.0, 5.0]), pd.Series([100.0, 0.0]))
    assert r.iloc[0] == pytest.approx(10.0)
    assert pd.isna(r.iloc[1])


# ---------------------------------------------------------------------------
# Known sample portfolio P001 (the Project Guide example)
# ---------------------------------------------------------------------------

@pytest.fixture
def p001():
    return analyze_portfolio(FIXTURE, portfolio_id="P001")


def test_p001_summary(p001):
    s = p001["summary"]
    assert s["invested_value"] == 53500.00
    assert s["current_value"] == 60200.00
    assert s["pnl"] == 6700.00
    assert s["return_pct"] == 12.52
    assert s["number_of_holdings"] == 3
    assert s["gainers"] == 3 and s["losers"] == 0
    assert s["top_gainers"][0]["symbol"] == "TCS"
    assert s["largest_pnl_detractor"] is None


def test_p001_holdings(p001):
    h = {x["symbol"]: x for x in p001["holdings"]}
    assert h["RELIANCE"]["invested_value"] == 24000
    assert h["RELIANCE"]["current_value"] == 26500
    assert h["RELIANCE"]["pnl"] == 2500
    assert h["RELIANCE"]["return_pct"] == 10.42
    assert h["TCS"]["return_pct"] == 17.14
    assert h["INFY"]["return_pct"] == 10.0
    # sorted by current value, largest first
    assert [x["symbol"] for x in p001["holdings"]] == ["RELIANCE", "TCS", "INFY"]


def test_weights_and_contributions_add_up(p001):
    weights = sum(x["weight_pct"] for x in p001["holdings"])
    contrib = sum(x["contribution_pct"] for x in p001["holdings"])
    assert weights == pytest.approx(100, abs=0.05)
    assert contrib == pytest.approx(p001["summary"]["return_pct"], abs=0.05)


def test_p001_sector_allocation(p001):
    sectors = {x["name"]: x for x in p001["allocation"]["by_sector"]}
    assert sectors["IT"]["weight_pct"] == 55.98
    assert sectors["Energy"]["weight_pct"] == 44.02
    assert sectors["IT"]["holdings"] == 2
    assert p001["allocation"]["by_sector"][0]["name"] == "IT"   # largest first
    assert p001["allocation"]["number_of_asset_types"] == 1


# ---------------------------------------------------------------------------
# Mixed portfolio P002 (losses + several asset types)
# ---------------------------------------------------------------------------

def test_p002_mixed_portfolio():
    r = analyze_portfolio(FIXTURE, portfolio_id="P002")
    s = r["summary"]
    assert s["invested_value"] == 132000
    assert s["current_value"] == 133000
    assert s["pnl"] == 1000
    assert s["return_pct"] == 0.76
    assert s["gainers"] == 2 and s["losers"] == 2
    assert s["total_gains"] == 8000 and s["total_losses"] == -7000
    assert s["top_losers"][0]["symbol"] == "ITC"           # -11.11%
    assert s["largest_pnl_contributor"]["symbol"] == "SGBAUG30"

    assets = {x["name"]: x for x in r["allocation"]["by_asset_type"]}
    assert assets["Equity"]["current_value"] == 70000
    assert assets["Equity"]["weight_pct"] == 52.63
    assert assets["Gold"]["weight_pct"] == 27.07
    assert assets["ETF"]["weight_pct"] == 20.30
    # Gold has grown from 22.73% of invested value to 27.07% of current value
    assert assets["Gold"]["drift_pct"] == pytest.approx(4.34, abs=0.01)


# ---------------------------------------------------------------------------
# Edge cases (Project Guide §20)
# ---------------------------------------------------------------------------

def test_empty_csv():
    with pytest.raises(PortfolioDataError):
        analyze_portfolio(io.StringIO(""))
    with pytest.raises(PortfolioDataError):
        analyze_portfolio(csv(""))


def test_missing_columns():
    with pytest.raises(PortfolioDataError, match="Missing required columns"):
        analyze_portfolio(io.StringIO("symbol,quantity\nTCS,5\n"))


def test_invalid_values():
    with pytest.raises(PortfolioDataError, match="Non-numeric"):
        analyze_portfolio(csv("P1,TCS,TCS,Equity,IT,five,3500,4100\n"))
    with pytest.raises(PortfolioDataError, match="Negative"):
        analyze_portfolio(csv("P1,TCS,TCS,Equity,IT,-5,3500,4100\n"))
    with pytest.raises(PortfolioDataError, match="average_buy_price"):
        analyze_portfolio(csv("P1,TCS,TCS,Equity,IT,5,,4100\n"))


def test_zero_quantity_is_skipped():
    r = analyze_portfolio(csv(
        "P1,TCS,TCS,Equity,IT,5,3500,4100\n"
        "P1,INFY,Infosys,Equity,IT,0,1500,1650\n"
    ))
    assert r["summary"]["number_of_holdings"] == 1
    assert any("zero quantity" in w for w in r["warnings"])


def test_all_zero_quantity_raises():
    with pytest.raises(PortfolioDataError):
        analyze_portfolio(csv("P1,TCS,TCS,Equity,IT,0,3500,4100\n"))


def test_missing_current_price_falls_back_to_cost():
    r = analyze_portfolio(csv(
        "P1,TCS,TCS,Equity,IT,5,3500,4100\n"
        "P1,INFY,Infosys,Equity,IT,8,1500,\n"
    ))
    infy = next(h for h in r["holdings"] if h["symbol"] == "INFY")
    assert infy["price_missing"] is True
    assert infy["current_value"] == 12000 and infy["pnl"] == 0
    assert any("Current price missing" in w for w in r["warnings"])


def test_duplicate_symbols_are_merged():
    r = analyze_portfolio(csv(
        "P1,TCS,TCS,Equity,IT,5,3000,4000\n"
        "P1,tcs,TCS,Equity,IT,5,4000,4000\n"
    ))
    h = r["holdings"][0]
    assert r["summary"]["number_of_holdings"] == 1
    assert h["quantity"] == 10
    assert h["average_buy_price"] == 3500     # quantity-weighted
    assert h["invested_value"] == 35000


def test_missing_sector_defaults_to_unknown():
    df, _ = load_portfolio(csv("P1,TCS,,,,5,3500,4100\n"))
    assert df.loc[0, "sector"] == "Unknown"
    assert df.loc[0, "asset_type"] == "Unknown"
    assert df.loc[0, "company_name"] == "TCS"


def test_single_stock_portfolio():
    r = analyze_portfolio(csv("P1,TCS,TCS,Equity,IT,5,3500,4100\n"))
    assert r["holdings"][0]["weight_pct"] == 100.0
    assert r["allocation"]["by_sector"][0]["weight_pct"] == 100.0
    assert r["allocation"]["by_security"][0]["weight_pct"] == 100.0


def test_large_portfolio():
    rows = "".join(
        f"P1,S{i},Stock {i},Equity,Sector{i % 10},{i + 1},100,{100 + (i % 7) - 3}\n"
        for i in range(500)
    )
    r = analyze_portfolio(csv(rows))
    assert r["summary"]["number_of_holdings"] == 500
    assert r["allocation"]["number_of_sectors"] == 10
    assert sum(x["weight_pct"] for x in r["allocation"]["by_sector"]) == pytest.approx(100, abs=0.05)


def test_unknown_portfolio_id():
    with pytest.raises(PortfolioDataError, match="No holdings"):
        analyze_portfolio(FIXTURE, portfolio_id="P999")


def test_multiple_portfolios_without_filter_warns():
    r = analyze_portfolio(FIXTURE)
    assert r["portfolio_id"] is None
    assert r["summary"]["number_of_holdings"] == 7
    assert any("several portfolios" in w for w in r["warnings"])


def test_dataframe_input_and_json_output():
    df = pd.read_csv(FIXTURE)
    r = analyze_portfolio(df, portfolio_id="P002")
    json.dumps(r)    # must be serialisable for FastAPI
    assert analyze_portfolio(df, portfolio_id="P002") == r   # deterministic


# ---------------------------------------------------------------------------
# Integration with the Risk & Diversification module (Soumil, feature/risk)
# ---------------------------------------------------------------------------

def test_holdings_frame_feeds_risk_engine():
    """compute_holdings() output must be accepted by risk_engine as-is."""
    risk_engine = pytest.importorskip("risk_engine")
    from analytics import compute_holdings

    df, _ = load_portfolio(FIXTURE)
    holdings = compute_holdings(df[df["portfolio_id"] == "P001"])
    risk = risk_engine.analyze_portfolio_risk(holdings)
    conc = risk_engine.calculate_concentration(holdings)

    ours = analyze_portfolio(FIXTURE, portfolio_id="P001")["allocation"]["by_security"]
    assert conc["largest_holding_pct"] == ours[0]["weight_pct"]   # same numbers on dashboard
    assert risk is not None


# ---------------------------------------------------------------------------
# Blank symbol (bug B013): must be rejected on every pandas version
# ---------------------------------------------------------------------------

def test_blank_symbol_is_rejected():
    with pytest.raises(PortfolioDataError, match="symbol"):
        analyze_portfolio(pd.read_csv(csv("P001,,No Symbol Ltd,Equity,IT,1,100,100\n")))


def test_blank_symbol_among_valid_rows_is_rejected():
    rows = "P001,TCS,Tata,Equity,IT,1,100,100\nP001,,No Symbol Ltd,Equity,IT,1,100,100\n"
    with pytest.raises(PortfolioDataError):
        analyze_portfolio(pd.read_csv(csv(rows)))
