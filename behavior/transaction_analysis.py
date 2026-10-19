"""Validation, transaction summaries, and FIFO holding-duration analysis."""

import csv
import math
from collections import defaultdict, deque
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED_FIELDS = (
    "transaction_id", "portfolio_id", "date", "symbol",
    "transaction_type", "quantity", "price",
)


def load_transactions(path):
    """Read a CSV; return records for analyze_behavior to validate."""
    with open(path, newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        missing = set(REQUIRED_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing CSV columns: " + ", ".join(sorted(missing)))
        return list(reader)


def parse_date(value):
    """Require a calendar date in YYYY-MM-DD format."""
    if not isinstance(value, str):
        raise ValueError("Dates must be YYYY-MM-DD strings")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Invalid date: " + value) from error
    if parsed.isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD format")
    return parsed


def validate_transactions(records, portfolio_id=None):
    """Validate every record before selecting one portfolio; never drop bad rows."""
    result, seen = [], set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Row {index}: expected a dictionary")
        missing = set(REQUIRED_FIELDS) - record.keys()
        if missing:
            raise ValueError(f"Row {index}: missing fields {sorted(missing)}")
        row = {}
        for key in ("transaction_id", "portfolio_id", "symbol", "transaction_type"):
            value = record[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Row {index}: {key} must be a non-empty string")
            row[key] = value.strip()
        row["symbol"] = row["symbol"].upper()
        row["transaction_type"] = row["transaction_type"].upper()
        if row["transaction_type"] not in ("BUY", "SELL"):
            raise ValueError(f"Row {index}: transaction_type must be BUY or SELL")
        row["date"] = parse_date(record["date"])
        for key in ("quantity", "price"):
            try:
                number = Decimal(str(record[key]))
                representable = math.isfinite(float(number)) and float(number) > 0
            except (InvalidOperation, ValueError, OverflowError):
                representable = False
            if not representable or not number.is_finite() or number <= 0:
                raise ValueError(f"Row {index}: {key} must be finite and positive")
            row[key] = number
        if not math.isfinite(float(row["quantity"] * row["price"])):
            raise ValueError(f"Row {index}: transaction value is too large")
        identity = (row["portfolio_id"], row["transaction_id"])
        if identity in seen:
            raise ValueError(f"Row {index}: duplicate transaction_id in portfolio")
        seen.add(identity)
        result.append(row)
    portfolios = {row["portfolio_id"] for row in result}
    if portfolio_id is not None:
        if not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise ValueError("portfolio_id must be a non-empty string")
        portfolio_id = portfolio_id.strip()
        result = [row for row in result if row["portfolio_id"] == portfolio_id]
    elif len(portfolios) > 1:
        raise ValueError("Select portfolio_id when records contain multiple portfolios")
    # Python's stable sort preserves supplied row order for equal dates.
    return sorted(result, key=lambda row: row["date"])


def transaction_summary(rows):
    buys = [row for row in rows if row["transaction_type"] == "BUY"]
    sells = [row for row in rows if row["transaction_type"] == "SELL"]
    by_symbol = defaultdict(lambda: {"buy_count": 0, "sell_count": 0})
    for row in rows:
        key = "buy_count" if row["transaction_type"] == "BUY" else "sell_count"
        by_symbol[row["symbol"]][key] += 1
    buy_value = sum((row["quantity"] * row["price"] for row in buys), Decimal(0))
    sell_value = sum((row["quantity"] * row["price"] for row in sells), Decimal(0))
    if not all(math.isfinite(float(value)) for value in (buy_value, sell_value)):
        raise ValueError("Aggregate transaction value is too large")
    return {
        "total_trades": len(rows), "buy_count": len(buys), "sell_count": len(sells),
        "buy_percentage": round(100 * len(buys) / len(rows), 2) if rows else None,
        "sell_percentage": round(100 * len(sells) / len(rows), 2) if rows else None,
        "buy_value": float(buy_value), "sell_value": float(sell_value),
        "by_symbol": dict(sorted(by_symbol.items())),
    }


def holding_analysis(rows, as_of):
    """Match sells to earlier buys; unknown opening inventory remains unmatched."""
    lots = defaultdict(deque)
    matches, unmatched = [], []
    for row in rows:
        symbol = row["symbol"]
        if row["transaction_type"] == "BUY":
            lots[symbol].append({**row, "remaining": row["quantity"]})
            continue
        remaining = row["quantity"]
        while remaining > 0 and lots[symbol]:
            lot = lots[symbol][0]
            quantity = min(remaining, lot["remaining"])
            matches.append({
                "symbol": symbol, "buy_transaction_id": lot["transaction_id"],
                "sell_transaction_id": row["transaction_id"],
                "buy_date": lot["date"].isoformat(), "sell_date": row["date"].isoformat(),
                "quantity": float(quantity), "holding_days": (row["date"] - lot["date"]).days,
                "buy_price": float(lot["price"]), "sell_price": float(row["price"]),
                "return_percentage": float((row["price"] / lot["price"] - 1) * 100),
            })
            remaining -= quantity
            lot["remaining"] -= quantity
            if lot["remaining"] == 0:
                lots[symbol].popleft()
        if remaining > 0:
            unmatched.append({"transaction_id": row["transaction_id"], "symbol": symbol,
                              "unmatched_quantity": float(remaining)})
    open_lots = [
        {"symbol": symbol, "buy_transaction_id": lot["transaction_id"],
         "quantity": float(lot["remaining"]), "age_days": (as_of - lot["date"]).days}
        for symbol in sorted(lots) for lot in lots[symbol]
    ]
    matched_quantity = sum(item["quantity"] for item in matches)
    return {
        "method": "FIFO", "matches": matches, "open_lots": open_lots,
        "unmatched_sells": unmatched,
        "average_closed_holding_days": (
            round(sum(item["holding_days"] * item["quantity"] for item in matches)
                  / matched_quantity, 2) if matched_quantity else None
        ),
        "minimum_closed_holding_days": min((item["holding_days"] for item in matches), default=None),
        "maximum_closed_holding_days": max((item["holding_days"] for item in matches), default=None),
    }
