"""Trade frequency and a configurable high-activity proxy."""

from collections import Counter


def trading_frequency(rows, start, end, daily_trade_threshold=5):
    if type(daily_trade_threshold) is not int or daily_trade_threshold < 1:
        raise ValueError("daily_trade_threshold must be a positive integer")
    counts = Counter(row["date"].isoformat() for row in rows)
    days = (end - start).days + 1
    flagged = {day: count for day, count in sorted(counts.items())
               if count > daily_trade_threshold}
    return {
        "observation_start": start.isoformat(), "observation_end": end.isoformat(),
        "calendar_days": days, "active_days": len(counts),
        "trades_per_calendar_day": round(len(rows) / days, 4),
        "trades_per_active_day": round(len(rows) / len(counts), 4) if counts else None,
        "daily_trade_counts": dict(sorted(counts.items())),
        "overtrading_indicator": {
            "label": "high_activity_proxy", "daily_trade_threshold": daily_trade_threshold,
            "flagged": bool(flagged), "flagged_days": flagged,
            "flagged_active_day_fraction": len(flagged) / len(counts) if counts else None,
        },
    }
