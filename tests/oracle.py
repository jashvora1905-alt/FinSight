"""Independent, deterministic reference calculations (pandas/plain Python only).
Delivered modules are compared against these. Values are UNROUNDED; modules round to
2 dp (money, %) / 6 dp (HHI), so compare with pytest.approx(abs=0.01) or ~1e-4 on 0-1 weights."""
import pandas as pd


def enrich(df):
    d = df.copy()
    d["invested"] = d["quantity"] * d["average_buy_price"]
    d["value"] = d["quantity"] * d["current_price"]
    d["pnl"] = d["value"] - d["invested"]
    d["weight"] = d["value"] / d["value"].sum()
    return d


def summary(df):
    d = enrich(df)
    inv, val = d["invested"].sum(), d["value"].sum()
    return {"total_invested": inv, "current_value": val,
            "total_pnl": val - inv, "return_pct": (val - inv) / inv * 100}


def hhi(df):
    return float((enrich(df)["weight"] ** 2).sum())


def top_weight(df):
    return float(enrich(df)["weight"].max())


def sector_weights(df):
    d = enrich(df)
    return (d.groupby("sector")["value"].sum() / d["value"].sum()).to_dict()


def net_positions(tx):
    s = tx.assign(signed=tx["quantity"].where(tx["transaction_type"] == "BUY", -tx["quantity"]))
    return s.groupby("symbol")["signed"].sum().to_dict()


def behavior(tx, max_days=7, loss_pct=5, daily_threshold=5):
    """FIFO matching, as in docs/behavior_methodology.md. Flagged match = sale held <= max_days
    with a loss of >= loss_pct. Score = 100 - 50*active-day flag fraction - 50*flagged qty fraction,
    available only with >=30 calendar days, >=10 trades, >=1 match and no unmatched sells."""
    t = tx.assign(date=pd.to_datetime(tx["date"])).sort_values("date", kind="stable")
    lots, matches, unmatched = {}, [], 0
    for r in t.itertuples():
        q = lots.setdefault(r.symbol, [])
        if r.transaction_type == "BUY":
            q.append([r.date, r.quantity, r.price])
            continue
        rem = r.quantity
        while rem > 0 and q:
            take = min(rem, q[0][1])
            matches.append({"sell_id": r.transaction_id, "qty": take,
                            "days": (r.date - q[0][0]).days,
                            "ret": (r.price / q[0][2] - 1) * 100})
            rem -= take
            q[0][1] -= take
            if q[0][1] == 0:
                q.pop(0)
        if rem > 0:
            unmatched += 1
    flagged = [m for m in matches if m["days"] <= max_days and m["ret"] <= -loss_pct + 1e-10]
    matched_qty = sum(m["qty"] for m in matches)
    per_day = t.groupby("date").size()
    activity_fraction = (per_day > daily_threshold).sum() / len(per_day) if len(per_day) else 0
    loss_fraction = sum(m["qty"] for m in flagged) / matched_qty if matched_qty else 0
    calendar_days = (t["date"].max() - t["date"].min()).days + 1 if len(t) else 0
    available = calendar_days >= 30 and len(t) >= 10 and bool(matches) and unmatched == 0
    counts = t["symbol"].value_counts()
    return {
        "total_trades": len(t),
        "buy_count": int((t["transaction_type"] == "BUY").sum()),
        "sell_count": int((t["transaction_type"] == "SELL").sum()),
        "short_hold_loss_sell_count": len({m["sell_id"] for m in flagged}),
        "flagged_sell_ids": sorted({m["sell_id"] for m in flagged}),
        "most_traded_symbol": counts.index[0] if len(counts) else None,
        "unmatched_sells": unmatched,
        "behavior_score": round(100 - 50 * activity_fraction - 50 * loss_fraction, 2) if available else None,
    }
