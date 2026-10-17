"""Short-hold loss-selling proxy; does not infer investor emotions."""

import math


def panic_selling_indicators(holdings, max_holding_days=7, minimum_loss_percentage=5):
    if type(max_holding_days) is not int or max_holding_days < 0:
        raise ValueError("max_holding_days must be a non-negative integer")
    if (isinstance(minimum_loss_percentage, bool)
            or not isinstance(minimum_loss_percentage, (int, float))
            or not math.isfinite(minimum_loss_percentage)
            or not 0 < minimum_loss_percentage <= 100):
        raise ValueError("minimum_loss_percentage must be in (0, 100]")
    matches = holdings["matches"]
    flagged = [match for match in matches
               if match["holding_days"] <= max_holding_days
               and match["return_percentage"] <= -minimum_loss_percentage + 1e-10]
    matched_quantity = sum(match["quantity"] for match in matches)
    return {
        "label": "short_hold_loss_selling_proxy",
        "status": "available" if matches else "insufficient_data",
        "flagged": bool(flagged) if matches else None,
        "max_holding_days": max_holding_days,
        "minimum_loss_percentage": minimum_loss_percentage,
        "flagged_matches": flagged,
        "flagged_sell_count": len({match["sell_transaction_id"] for match in flagged}),
        "flagged_matched_quantity_fraction": (
            sum(match["quantity"] for match in flagged) / matched_quantity
            if matched_quantity else None
        ),
        "limitation": "Transaction rules identify short-hold loss sales, not panic or intent. "
                      "No market-price history, trading strategy, fees or opening inventory is supplied.",
    }
