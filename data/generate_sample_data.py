"""Regenerates every CSV in data/. Run from repo root: python data/generate_sample_data.py

Schemas are the team-wide contract read by analytics, risk_engine and behavior:
  Portfolio:    portfolio_id, symbol, company_name, asset_type, sector, quantity,
                average_buy_price, current_price
  Transactions: transaction_id, portfolio_id, date (YYYY-MM-DD), symbol,
                transaction_type (BUY/SELL), quantity, price
(No fees column: no module reads it and the behaviour methodology states fees are not modelled.)

Sample portfolio and sample transactions reconcile on purpose:
net BUY - SELL quantity per symbol == quantity in sample_portfolio.csv (all under P001).
"""
import csv
from pathlib import Path

DATA = Path(__file__).parent
EDGE = DATA / "edge_cases"
EDGE.mkdir(exist_ok=True)

P_HEAD = ["portfolio_id", "symbol", "company_name", "asset_type", "sector",
          "quantity", "average_buy_price", "current_price"]
T_HEAD = ["transaction_id", "portfolio_id", "date", "symbol", "transaction_type", "quantity", "price"]
PID = "P001"

# (symbol, company_name, asset_type, sector, quantity, average_buy_price, current_price)
HOLDINGS = [
    ("RELIANCE", "Reliance Industries", "Equity", "Energy", 40, 2450.00, 2890.50),
    ("TCS", "Tata Consultancy Services", "Equity", "IT", 25, 3300.00, 3650.25),
    ("INFY", "Infosys", "Equity", "IT", 50, 1425.00, 1580.75),
    ("HDFCBANK", "HDFC Bank", "Equity", "Financials", 60, 1580.00, 1710.40),
    ("ICICIBANK", "ICICI Bank", "Equity", "Financials", 70, 957.14, 1245.60),
    ("ITC", "ITC Ltd", "Equity", "FMCG", 150, 380.00, 470.30),
    ("SUNPHARMA", "Sun Pharma", "Equity", "Healthcare", 30, 1050.00, 1620.00),
    ("TATAMOTORS", "Tata Motors", "Equity", "Auto", 80, 640.00, 720.80),
    ("PAYTM", "One97 Communications", "Equity", "Fintech", 40, 975.00, 720.15),
    ("NIFTYBEES", "Nippon India Nifty 50 ETF", "ETF", "Diversified", 200, 210.00, 265.40),
    ("GOLDBEES", "Nippon India Gold ETF", "ETF", "Commodities", 300, 42.00, 58.90),
    ("HDFCLIQUID", "HDFC Liquid Fund", "Mutual Fund", "Debt", 100, 4200.00, 4385.00),
]

# (date, symbol, type, qty, price)
TRADES = [
    ("2024-01-10", "RELIANCE", "BUY", 25, 2400),
    ("2024-01-15", "NIFTYBEES", "BUY", 100, 205),
    ("2024-01-22", "INFY", "BUY", 30, 1400),
    ("2024-01-30", "ICICIBANK", "BUY", 50, 900),
    ("2024-02-05", "TCS", "BUY", 25, 3300),
    ("2024-02-14", "TATAMOTORS", "BUY", 100, 640),
    ("2024-03-04", "GOLDBEES", "BUY", 300, 42),
    ("2024-03-12", "HDFCBANK", "BUY", 60, 1580),
    ("2024-04-08", "ITC", "BUY", 150, 380),
    ("2024-04-15", "HDFCLIQUID", "BUY", 100, 4200),
    ("2024-05-02", "PAYTM", "BUY", 60, 990),
    ("2024-05-09", "PAYTM", "SELL", 30, 940),   # held 7 days, -5.05%  -> flagged short-hold loss sale
    ("2024-05-16", "PAYTM", "BUY", 30, 960),
    ("2024-05-20", "SUNPHARMA", "BUY", 30, 1050),
    ("2024-05-23", "PAYTM", "SELL", 20, 910),   # FIFO vs 990 lot: 21 days, -8% -> loss but not short-hold
    ("2024-06-14", "RELIANCE", "BUY", 15, 2550),
    ("2024-07-01", "NIFTYBEES", "BUY", 100, 215),
    ("2024-08-26", "TATAMOTORS", "SELL", 20, 600),  # 6 months, -6% -> not short-hold
    ("2024-09-03", "INFY", "BUY", 30, 1450),
    ("2024-11-05", "ICICIBANK", "BUY", 20, 1100),
    ("2025-03-18", "INFY", "SELL", 10, 1520),   # profit sell
]


def write(path, head, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)


def raw(path, text):
    with open(path, "w", newline="") as f:
        f.write(text)


def hold(sym, qty, avg, cur, name=None, atype="Equity", sector="IT", pid=PID):
    return (pid, sym, name or sym, atype, sector, qty, avg, cur)


def tx(trades, pid=PID):
    return [(f"T{i:03d}", pid, d, s, ty, q, p) for i, (d, s, ty, q, p) in enumerate(trades, 1)]


write(DATA / "sample_portfolio.csv", P_HEAD, [(PID, *h) for h in HOLDINGS])
write(DATA / "sample_transactions.csv", T_HEAD, tx(TRADES))

# ---------------- edge-case portfolios ----------------
write(EDGE / "portfolio_empty.csv", P_HEAD, [])
write(EDGE / "portfolio_single_holding.csv", P_HEAD,
      [hold("TCS", 10, 3300.00, 3650.25, "Tata Consultancy Services")])
write(EDGE / "portfolio_concentrated.csv", P_HEAD, [
    hold("RELIANCE", 400, 2450.00, 2890.50, "Reliance Industries", sector="Energy"),
    hold("ITC", 20, 380.00, 470.30, "ITC Ltd", sector="FMCG"),
    hold("GOLDBEES", 50, 42.00, 58.90, "Nippon India Gold ETF", "ETF", "Commodities"),
])
write(EDGE / "portfolio_all_losses.csv", P_HEAD, [
    hold("PAYTM", 40, 980.00, 720.15, "One97 Communications", sector="Fintech"),
    hold("TATAMOTORS", 80, 900.00, 720.80, "Tata Motors", sector="Auto"),
])
# valid for the modules, but flagged by the strict reference validator or producing warnings
write(EDGE / "portfolio_duplicates.csv", P_HEAD, [         # merged -> qty 15, avg 3333.33
    hold("TCS", 10, 3300.00, 3650.25), hold("TCS", 5, 3400.00, 3650.25)])
write(EDGE / "portfolio_zero_quantity.csv", P_HEAD, [      # INFY row skipped with warning
    hold("TCS", 10, 3300.00, 3650.25), hold("INFY", 0, 1400.00, 1580.00)])
write(EDGE / "portfolio_zero_current_price.csv", P_HEAD, [  # avg buy used, price_missing flagged
    hold("TCS", 10, 3300.00, 0), hold("INFY", 10, 1400.00, 1580.00)])
write(EDGE / "portfolio_multi_portfolio.csv", P_HEAD, [    # warning unless portfolio_id supplied
    hold("TCS", 10, 3300.00, 3650.25, pid="P001"), hold("INFY", 10, 1400.00, 1580.00, pid="P002")])
# invalid for every module (ValueError)
raw(EDGE / "portfolio_missing_column.csv",
    "portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price\n"
    "P001,TCS,Tata Consultancy Services,Equity,IT,10,3300\n")      # no current_price
write(EDGE / "portfolio_negative_quantity.csv", P_HEAD, [hold("TCS", -5, 3300.00, 3650.25)])
write(EDGE / "portfolio_non_numeric_price.csv", P_HEAD, [
    hold("TCS", 10, 3300.00, 3650.25), hold("INFY", 10, 1400.00, "abc")])
write(EDGE / "portfolio_blank_symbol.csv", P_HEAD, [hold("", 10, 100.00, 100.00)])
write(EDGE / "portfolio_zero_buy_price.csv", P_HEAD, [hold("TCS", 10, 0, 3650.25)])
write(EDGE / "portfolio_invalid_values.csv", P_HEAD, [     # several problems at once
    hold("TCS", -5, 3300, 3650), hold("INFY", 10, "abc", 1580),
    hold("", 10, 100, 100), hold("ITC", 10, 380, 0)])

# ---------------- edge-case transactions ----------------
write(EDGE / "transactions_empty.csv", T_HEAD, [])
write(EDGE / "transactions_oversell.csv", T_HEAD, tx([
    ("2024-01-10", "TCS", "BUY", 10, 3300),
    ("2024-02-10", "TCS", "SELL", 15, 3400)]))                 # 5 shares unmatched
write(EDGE / "transactions_invalid.csv", T_HEAD, [
    ("T001", PID, "2024-01-10", "TCS", "HOLD", 10, 3300),      # bad type
    ("T002", PID, "not-a-date", "TCS", "BUY", 10, 3300),       # bad date
    ("T003", PID, "2024-01-12", "TCS", "BUY", 10, -5)])        # negative price
write(EDGE / "transactions_multi_portfolio.csv", T_HEAD, [
    ("T001", "P001", "2024-01-10", "TCS", "BUY", 10, 3300),
    ("T002", "P002", "2024-01-11", "INFY", "BUY", 10, 1400)])
write(EDGE / "transactions_short_history.csv", T_HEAD, tx([     # <10 trades, <30 days
    ("2024-03-01", "ABC", "BUY", 10, 100),
    ("2024-03-03", "ABC", "SELL", 5, 110),
    ("2024-03-05", "ABC", "BUY", 5, 105)]))
write(EDGE / "transactions_overtrading.csv", T_HEAD, tx(      # 7 trades on one day (> threshold 5)
    [("2024-03-01", "ABC", "BUY", 1, 100)] * 6 + [
        ("2024-03-01", "ABC", "SELL", 1, 101),
        ("2024-04-15", "ABC", "BUY", 1, 100),
        ("2024-05-10", "ABC", "BUY", 1, 100),
        ("2024-06-20", "ABC", "SELL", 1, 110),
        ("2024-07-30", "ABC", "BUY", 1, 100),
        ("2024-08-30", "ABC", "SELL", 1, 120)]))

print("sample data written to", DATA)
