"""Controlled transaction histories; run from repository root with unittest."""

import json
import tempfile
import unittest
from pathlib import Path

from behavior import analyze_behavior, load_transactions


def trade(identifier, day="2026-01-01", kind="BUY", quantity=10, price=100,
          symbol="ABC", portfolio="P001"):
    return dict(transaction_id=identifier, portfolio_id=portfolio, date=day,
                symbol=symbol, transaction_type=kind, quantity=quantity, price=price)


class BehaviorTests(unittest.TestCase):
    def test_fifo_partial_and_multiple_lots(self):
        rows = [trade("B1", quantity=10), trade("B2", "2026-01-05", quantity=5, price=200),
                trade("S1", "2026-01-11", "SELL", 12, 150)]
        result = analyze_behavior(rows, observation_end="2026-01-31")
        holdings = result["holdings"]
        self.assertEqual([item["quantity"] for item in holdings["matches"]], [10, 2])
        self.assertEqual([item["holding_days"] for item in holdings["matches"]], [10, 6])
        self.assertEqual(holdings["average_closed_holding_days"], 9.33)
        self.assertEqual(holdings["open_lots"][0]["quantity"], 3)
        self.assertEqual(holdings["open_lots"][0]["age_days"], 26)
        self.assertEqual(result["panic_selling_indicator"]["flagged_sell_count"], 1)

    def test_unsorted_history(self):
        result = analyze_behavior([trade("S", "2026-01-04", "SELL"), trade("B")])
        self.assertEqual(result["holdings"]["matches"][0]["holding_days"], 3)

    def test_loss_and_days_boundaries(self):
        for day, price, flagged in [("2026-01-08", 95, True),
                                     ("2026-01-09", 95, False),
                                     ("2026-01-08", 96, False)]:
            with self.subTest(day=day, price=price):
                result = analyze_behavior([trade("B"), trade("S", day, "SELL", price=price)])
                self.assertEqual(result["panic_selling_indicator"]["flagged"], flagged)

    def test_frequency_threshold_and_calendar_denominator(self):
        rows = [trade(str(i), quantity=1) for i in range(6)]
        result = analyze_behavior(rows, observation_end="2026-01-30")
        self.assertTrue(result["frequency"]["overtrading_indicator"]["flagged"])
        self.assertEqual(result["frequency"]["trades_per_calendar_day"], 0.2)
        result = analyze_behavior(rows[:5])
        self.assertFalse(result["frequency"]["overtrading_indicator"]["flagged"])

    def test_known_score(self):
        rows = [trade(f"B{i}", quantity=1) for i in range(6)]
        rows += [trade(f"S{i}", "2026-01-08", "SELL", 1, 95) for i in range(4)]
        result = analyze_behavior(rows, observation_end="2026-01-30")
        # One of two active days flagged: 25 penalty. All closed units flagged: 50.
        self.assertEqual(result["behavior_score"]["value"], 25)
        self.assertEqual(result["behavior_score"]["status"], "available")
        json.dumps(result, allow_nan=False)

    def test_empty_history(self):
        self.assertIsNone(analyze_behavior([])["behavior_score"]["value"])
        result = analyze_behavior([], observation_start="2026-01-01", observation_end="2026-01-30")
        self.assertEqual(result["frequency"]["trades_per_calendar_day"], 0)
        self.assertIsNone(result["panic_selling_indicator"]["flagged"])
        self.assertIsNone(result["behavior_score"]["value"])

    def test_buy_only_not_automatically_perfect(self):
        result = analyze_behavior([trade(str(i)) for i in range(10)],
                                  observation_end="2026-02-01")
        self.assertIsNone(result["behavior_score"]["value"])
        self.assertIsNone(result["holdings"]["average_closed_holding_days"])

    def test_unmatched_sale_does_not_consume_future_buy(self):
        result = analyze_behavior([trade("S", kind="SELL"), trade("B", "2026-01-05")])
        self.assertEqual(result["holdings"]["matches"], [])
        self.assertEqual(result["holdings"]["unmatched_sells"][0]["unmatched_quantity"], 10)
        self.assertEqual(result["holdings"]["open_lots"][0]["quantity"], 10)

    def test_oversell_keeps_valid_partial_match(self):
        result = analyze_behavior([trade("B", quantity=2), trade("S", "2026-01-02", "SELL", 5)])
        self.assertEqual(result["holdings"]["matches"][0]["quantity"], 2)
        self.assertEqual(result["holdings"]["unmatched_sells"][0]["unmatched_quantity"], 3)
        self.assertIsNone(result["behavior_score"]["value"])

    def test_fractional_lots(self):
        rows = [trade("B1", quantity="0.1"), trade("B2", quantity="0.2"),
                trade("S", "2026-01-02", "SELL", "0.3")]
        result = analyze_behavior(rows)
        self.assertEqual(result["holdings"]["unmatched_sells"], [])
        self.assertEqual(result["holdings"]["open_lots"], [])

    def test_portfolio_isolation(self):
        rows = [trade("1"), trade("1", portfolio="P002", kind="SELL")]
        with self.assertRaises(ValueError):
            analyze_behavior(rows)
        result = analyze_behavior(rows, portfolio_id="P002")
        self.assertEqual(result["summary"]["total_trades"], 1)
        self.assertEqual(result["holdings"]["matches"], [])

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze_behavior([trade("1"), trade("1")])

    def test_bad_values(self):
        for field, value in [("quantity", 0), ("quantity", -1), ("price", "NaN"),
                             ("price", "Infinity"), ("price", None), ("price", True),
                             ("date", "2026-02-30"), ("date", "20260101"),
                             ("transaction_type", "HOLD"), ("symbol", "")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                analyze_behavior([{**trade("1"), field: value}])

    def test_missing_field(self):
        row = trade("1")
        del row["price"]
        with self.assertRaisesRegex(ValueError, "missing"):
            analyze_behavior([row])

    def test_window_validation(self):
        for start, end in [("2026-01-02", "2026-01-01"),
                           ("2026-01-02", "2026-02-01"), ("", "2026-02-01")]:
            with self.subTest(start=start), self.assertRaises(ValueError):
                analyze_behavior([trade("1")], observation_start=start, observation_end=end)

    def test_invalid_configuration_even_with_empty_data(self):
        for config in [dict(daily_trade_threshold=0), dict(daily_trade_threshold=True),
                       dict(max_holding_days=-1), dict(minimum_loss_percentage=float("nan"))]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                analyze_behavior([], **config)

    def test_same_date_input_order_preserved(self):
        result = analyze_behavior([trade("S", kind="SELL"), trade("B")])
        self.assertEqual(len(result["holdings"]["unmatched_sells"]), 1)

    def test_does_not_modify_input(self):
        rows = [trade("B", symbol=" abc ")]
        before = json.dumps(rows)
        analyze_behavior(rows)
        self.assertEqual(json.dumps(rows), before)

    def test_csv_loader(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transactions.csv"
            path.write_text("transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price\n"
                            "T1,P001,2026-01-01,ABC,BUY,10,100\n", encoding="utf-8")
            self.assertEqual(analyze_behavior(load_transactions(path))["summary"]["buy_value"], 1000)
            path.write_text("symbol,quantity\nABC,10\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing CSV columns"):
                load_transactions(path)


if __name__ == "__main__":
    unittest.main()
