"""Public entry point and transparent experimental scoring methodology."""

import json

from .panic_selling import panic_selling_indicators
from .trading_frequency import trading_frequency
from .transaction_analysis import (
    holding_analysis, parse_date, transaction_summary, validate_transactions,
)


def analyze_behavior(records, portfolio_id=None, *, observation_start=None,
                     observation_end=None, daily_trade_threshold=5,
                     max_holding_days=7, minimum_loss_percentage=5):
    """Return JSON-safe results for one portfolio. Invalid input raises ValueError.

    records is a list/iterable of dictionaries, e.g. pandas df.to_dict('records').
    Optional observation dates define an inclusive window containing ALL records;
    the caller should supply all available earlier buys for accurate FIFO matches.
    """
    rows = validate_transactions(records, portfolio_id)
    if not rows and (observation_start is None or observation_end is None):
        # Validate supplied parameters even when data is empty.
        if observation_start is not None:
            parse_date(observation_start)
        if observation_end is not None:
            parse_date(observation_end)
        trading_frequency([], parse_date("2000-01-01"), parse_date("2000-01-01"), daily_trade_threshold)
        panic_selling_indicators({"matches": []}, max_holding_days, minimum_loss_percentage)
        return {
            "methodology_version": "behavior-v1", "portfolio_id": portfolio_id,
            "status": "insufficient_data", "summary": transaction_summary([]),
            "frequency": None, "holdings": None, "panic_selling_indicator": None,
            "behavior_score": {"value": None, "status": "insufficient_data",
                               "reasons": ["No transactions; supply both observation dates for window metrics."]},
            "warnings": ["No transactions found for the selected portfolio."],
        }
    start = parse_date(observation_start) if observation_start is not None else rows[0]["date"]
    end = parse_date(observation_end) if observation_end is not None else rows[-1]["date"]
    if end < start:
        raise ValueError("observation_end must be on or after observation_start")
    if rows and (rows[0]["date"] < start or rows[-1]["date"] > end):
        raise ValueError("Observation window must contain all selected transactions")
    frequency = trading_frequency(rows, start, end, daily_trade_threshold)
    holdings = holding_analysis(rows, end)
    panic = panic_selling_indicators(holdings, max_holding_days, minimum_loss_percentage)
    summary = transaction_summary(rows)
    reasons = []
    if frequency["calendar_days"] < 30:
        reasons.append("At least 30 calendar days of observation are required.")
    if len(rows) < 10:
        reasons.append("At least 10 transactions are required.")
    if not holdings["matches"]:
        reasons.append("At least one matched purchase and sale is required.")
    if holdings["unmatched_sells"]:
        reasons.append("Unmatched sales prevent a complete holding-history assessment.")
    activity_fraction = frequency["overtrading_indicator"]["flagged_active_day_fraction"]
    loss_fraction = panic["flagged_matched_quantity_fraction"]
    score = {
        "value": None, "status": "insufficient_data", "reasons": reasons,
        "scale": {"minimum": 0, "maximum": 100},
        "formula": "100 - 50 * flagged_active_day_fraction - 50 * flagged_matched_quantity_fraction",
        "components": {"activity_penalty": None, "short_hold_loss_penalty": None},
        "interpretation": "Experimental rule-based indicator; higher means fewer configured flags. "
                          "It is not a validated measure of investor skill or psychological health.",
    }
    if not reasons:
        activity_penalty = 50 * activity_fraction
        loss_penalty = 50 * loss_fraction
        score.update(value=round(max(0, min(100, 100 - activity_penalty - loss_penalty)), 2),
                     status="available", components={"activity_penalty": round(activity_penalty, 4),
                                                     "short_hold_loss_penalty": round(loss_penalty, 4)})
    warnings = [
        "Thresholds and equal score weights are prototype assumptions, not financial standards.",
        "Same-date transaction order follows input row order; dates do not establish intraday timing.",
        "Holding statistics cover matched quantities only; open positions are reported separately.",
        "Quantity-weighted statistics across symbols are influenced by share denominations.",
        "No corporate-action adjustments, fees, short sales or opening holdings are modeled.",
    ]
    if observation_start is None or observation_end is None:
        warnings.append("Unspecified observation boundaries use first/last transaction dates; inactivity outside them is unknown.")
    if holdings["unmatched_sells"]:
        warnings.append("Some sales lack earlier purchases in the supplied history; no holding period was invented.")
    result = {
        "methodology_version": "behavior-v1",
        "portfolio_id": rows[0]["portfolio_id"] if rows else portfolio_id,
        "status": "available" if rows else "insufficient_data",
        "summary": summary, "frequency": frequency, "holdings": holdings,
        "panic_selling_indicator": panic, "behavior_score": score, "warnings": warnings,
    }
    # Reject extreme derived values rather than returning invalid JSON numbers.
    try:
        json.dumps(result, allow_nan=False)
    except ValueError as error:
        raise ValueError("Derived metrics exceed the supported numeric range") from error
    return result
