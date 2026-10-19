"""Reference tests for Prisha's behavior module (FIFO holdings, short-hold loss proxy, score rules)."""
import json

import pytest

from tests import adapters, oracle
from tests.contract import resolve


def test_counts_and_flags_match_oracle(transactions):
    got, exp = resolve("behavior", "analyze")(transactions), oracle.behavior(transactions)
    for k in ("total_trades", "buy_count", "sell_count", "most_traded_symbol", "short_hold_loss_sell_count"):
        assert got[k] == exp[k], k


def test_known_sample_facts(transactions):
    got = resolve("behavior", "analyze")(transactions)
    assert (got["total_trades"], got["buy_count"], got["sell_count"]) == (21, 17, 4)
    assert got["most_traded_symbol"] == "PAYTM"               # 4 trades in 3 weeks
    assert got["short_hold_loss_sell_count"] == 1             # only the 7-day, -5.05% PAYTM sale
    flagged = adapters.behavior_raw(transactions)["panic_selling_indicator"]["flagged_matches"]
    assert [m["sell_transaction_id"] for m in flagged] == ["T012"]


def test_behavior_score_matches_oracle(transactions):
    got = resolve("behavior", "analyze")(transactions)["behavior_score"]
    assert got == pytest.approx(oracle.behavior(transactions)["behavior_score"], abs=0.01)
    assert got == pytest.approx(81.25, abs=0.01)             # 100 - 50 * (30 flagged / 80 matched)


def test_counts_add_up(transactions):
    got = resolve("behavior", "analyze")(transactions)
    assert got["buy_count"] + got["sell_count"] == got["total_trades"]


def test_empty_history_does_not_crash(edge):
    r = adapters.behavior_raw(edge("transactions_empty"))
    assert r["status"] == "insufficient_data" and r["summary"]["total_trades"] == 0
    assert r["behavior_score"]["value"] is None


def test_short_history_has_no_score(edge):
    r = adapters.behavior_raw(edge("transactions_short_history"))
    assert r["behavior_score"]["value"] is None
    reasons = " ".join(r["behavior_score"]["reasons"])
    assert "30 calendar days" in reasons and "10 transactions" in reasons


def test_overtrading_day_is_flagged_and_scored(edge):
    df = edge("transactions_overtrading")
    r = adapters.behavior_raw(df)
    flag = r["frequency"]["overtrading_indicator"]
    assert flag["flagged"] is True and list(flag["flagged_days"]) == ["2024-03-01"]
    assert r["behavior_score"]["value"] == pytest.approx(oracle.behavior(df)["behavior_score"], abs=0.01)


def test_oversell_is_reported_not_rejected(edge):
    r = adapters.behavior_raw(edge("transactions_oversell"))
    assert r["holdings"]["unmatched_sells"][0]["unmatched_quantity"] == 5
    assert r["behavior_score"]["value"] is None
    assert any("lack earlier purchases" in w for w in r["warnings"])


def test_buy_only_history_has_no_matches(transactions):
    r = adapters.behavior_raw(transactions[transactions["transaction_type"] == "BUY"])
    assert r["summary"]["sell_count"] == 0 and r["holdings"]["matches"] == []
    assert r["panic_selling_indicator"]["flagged"] is None


def test_invalid_transactions_raise_value_error(edge):
    with pytest.raises(ValueError):
        adapters.behavior_raw(edge("transactions_invalid"))


def test_multi_portfolio_needs_portfolio_id(edge):
    df = edge("transactions_multi_portfolio")
    with pytest.raises(ValueError):
        adapters.behavior_raw(df)
    assert adapters.behavior_raw(df, portfolio_id="P002")["summary"]["total_trades"] == 1


def test_row_order_does_not_matter_when_dates_differ(transactions):
    f = resolve("behavior", "analyze")
    assert f(transactions) == f(transactions.sample(frac=1, random_state=7))


def test_output_is_json_safe(transactions):
    json.dumps(adapters.behavior_raw(transactions), allow_nan=False)
