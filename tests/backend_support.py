"""Shared helpers + fixtures for the backend tests (tests/test_backend_api.py, tests/test_health_engine.py).
Inline CSVs use the Project README "Data Structure" schema shared by analytics, risk_engine and behavior."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.main import app

PORTFOLIO = """portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price
P001,RELIANCE,Reliance Industries,Equity,Energy,10,2400,2650
P001,TCS,Tata Consultancy Services,Equity,IT,5,3500,4100
P001,INFY,Infosys,Equity,IT,8,1500,1650
"""

TWO_PORTFOLIOS = PORTFOLIO + "P002,HDFCBANK,HDFC Bank,Equity,Banking,20,1600,1500\n"

CONCENTRATED = """portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price
P001,AAA,A Ltd,Equity,IT,100,100,100
P001,BBB,B Ltd,Equity,IT,1,100,100
"""
SINGLE = "portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price\nP001,AAA,A Ltd,Equity,IT,10,100,100\n"
DIVERSIFIED = "portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price\n" + "\n".join(
    f"P001,S{i},Co {i},Equity,{sec},10,100,100" for i, sec in enumerate(
        ["IT", "Banking", "Energy", "Pharma", "FMCG", "Auto", "Metals", "Telecom", "Infra", "Cement", "Retail", "Power"])) + "\n"

# the parity datasets exercise every loader rule: merging duplicates, zero quantity, zero price, blank text
QUIRKY = """portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price
P001,tcs,Tata Consultancy Services,Equity,IT,5,3500,4100
P001,TCS,Tata Consultancy Services,Equity,IT,5,3700,4100
P001,INFY,,Equity,,8,1500,0
P001,ZERO,Zero Qty Ltd,Equity,IT,0,100,100
P001,ITC,ITC,,FMCG,3,400,
"""


def make_transactions(portfolio_id="P001", n=12):
    rows = ["transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price"]
    for i in range(n):
        day = 1 + i * 4
        month, d = (1, day) if day <= 28 else (2, day - 28)
        kind = "BUY" if i % 2 == 0 else "SELL"
        rows.append(f"T{i},{portfolio_id},2026-{month:02d}-{d:02d},TCS,{kind},10,{100 + i}")
    return "\n".join(rows) + "\n"


def available_transactions(portfolio_id="P001"):
    """6 buys then 4 later sells over 60+ days: satisfies the behaviour module's minimum-data rules."""
    rows = ["transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price"]
    syms = ["TCS", "INFY", "ITC", "HDFCBANK", "RELIANCE", "LT"]
    for i, s in enumerate(syms):
        rows.append(f"B{i},{portfolio_id},2026-01-{1 + i * 6:02d},{s},BUY,10,100")
    for i, s in enumerate(syms[:4]):
        rows.append(f"S{i},{portfolio_id},2026-03-{2 + i * 5:02d},{s},SELL,5,120")
    return "\n".join(rows) + "\n"


def poor_transactions(portfolio_id="P001"):
    """Every matched sale is a short-hold loss (sold 2 days after buying at -8%); spans more than 30 days."""
    rows = ["transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price"]
    start = date(2026, 1, 1)
    for k in range(8):
        buy, sell = start + timedelta(days=k * 5), start + timedelta(days=k * 5 + 2)
        rows.append(f"PB{k},{portfolio_id},{buy},TCS,BUY,10,100")
        rows.append(f"PS{k},{portfolio_id},{sell},TCS,SELL,10,92")
    return "\n".join(rows) + "\n"


PRICE_HISTORY = "date,symbol,close\n" + "\n".join(
    f"2026-01-{d:02d},{s},{p}"
    for d in range(1, 11)
    for s, p in (("RELIANCE", 2400 + d * 10 + (d % 3) * 7), ("TCS", 3500 + d * 12 - (d % 4) * 9),
                 ("INFY", 1500 + d * 5 + (d % 2) * 11))
) + "\n"


def csv_file(text, name="data.csv"):
    return (name, text.encode(), "text/csv")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def post(client):
    def _post(portfolio=PORTFOLIO, transactions=None, price_history=None, **form):
        files = {}
        if portfolio is not None:
            files["portfolio"] = csv_file(portfolio, "portfolio.csv")
        if transactions is not None:
            files["transactions"] = csv_file(transactions, "transactions.csv")
        if price_history is not None:
            files["price_history"] = csv_file(price_history, "prices.csv")
        return client.post("/api/portfolio/upload", files=files or None, data=form)
    return _post
