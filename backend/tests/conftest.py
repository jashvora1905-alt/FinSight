"""Backend tests use small inline CSVs in the Project Guide §18 schema that analytics, risk_engine and
behavior all share (portfolio_id, symbol, company_name, asset_type, sector, ...)."""
import pytest
from fastapi.testclient import TestClient

from backend import store
from backend.main import app

PORTFOLIO = """portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price
P001,RELIANCE,Reliance Industries,Equity,Energy,10,2400,2650
P001,TCS,Tata Consultancy Services,Equity,IT,5,3500,4100
P001,INFY,Infosys,Equity,IT,8,1500,1650
"""

TWO_PORTFOLIOS = PORTFOLIO + "P002,HDFCBANK,HDFC Bank,Equity,Banking,20,1600,1500\n"


def make_transactions(portfolio_id="P001", n=12):
    rows = ["transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price"]
    for i in range(n):
        day = 1 + i * 4  # spans > 30 days
        month, d = (1, day) if day <= 28 else (2, day - 28)
        kind = "BUY" if i % 2 == 0 else "SELL"
        rows.append(f"T{i},{portfolio_id},2026-{month:02d}-{d:02d},TCS,{kind},10,{100 + i}")
    return "\n".join(rows) + "\n"


PRICE_HISTORY = "date,symbol,close\n" + "\n".join(
    f"2026-01-{d:02d},{s},{p}"
    for d in range(1, 11)
    for s, p in (("RELIANCE", 2400 + d * 10 + (d % 3) * 7), ("TCS", 3500 + d * 12 - (d % 4) * 9),
                 ("INFY", 1500 + d * 5 + (d % 2) * 11))
) + "\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def csv_file(text, name="data.csv"):
    return (name, text.encode(), "text/csv")


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
        return client.post("/api/upload", files=files or None, data=form)
    return _post
