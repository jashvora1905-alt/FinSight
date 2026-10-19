"""Thin adapters from the delivered modules to the shape our tests expect.
Verified against: analytics (Aditya), risk_engine (Soumil), behavior (Prisha).
Raw functions are exposed too, for tests of warnings / flags / null scores."""


def analytics_raw(df, **kw):
    from analytics import analyze_portfolio
    return analyze_portfolio(df, **kw)


def summary(df):
    s = analytics_raw(df)["summary"]
    return {"total_invested": s["invested_value"], "current_value": s["current_value"],
            "total_pnl": s["pnl"], "return_pct": s["return_pct"]}


def concentration_raw(df):
    from risk_engine import calculate_concentration
    return calculate_concentration(df)


def concentration(df):
    c = concentration_raw(df)
    return {"top_holding_weight": c["largest_holding_pct"] / 100, "hhi": c["holding_hhi"]}


def sectors(df):
    return {k: v / 100 for k, v in concentration_raw(df)["sector_weights_pct"].items()}


def diversification_raw(df):
    from risk_engine import analyze_diversification
    return analyze_diversification(df)


def diversification(df):
    return diversification_raw(df)["diversification_score"]


def behavior_raw(tx_df, **kw):
    from behavior import analyze_behavior
    return analyze_behavior(tx_df.to_dict("records"), **kw)


def analyze(tx_df, **kw):
    """summary counts + the fields our contract needs, derived from Prisha's output."""
    r = behavior_raw(tx_df, **kw)
    s = r["summary"]
    by_symbol = s["by_symbol"]
    most = max(by_symbol, key=lambda k: by_symbol[k]["buy_count"] + by_symbol[k]["sell_count"]) \
        if by_symbol else None
    panic = r["panic_selling_indicator"]
    return {"total_trades": s["total_trades"], "buy_count": s["buy_count"], "sell_count": s["sell_count"],
            "most_traded_symbol": most,
            "short_hold_loss_sell_count": panic["flagged_sell_count"] if panic else 0,
            "behavior_score": r["behavior_score"]["value"]}
