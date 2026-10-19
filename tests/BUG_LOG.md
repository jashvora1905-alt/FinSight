# FinSight Bug / Decision Log (owner: Atharva, E065)

Format: ID | found in | owner | test that proves it | what / expected vs actual | status.
Rule: every item has a test written first. Items marked DECISION were resolved by making the TEST follow the
delivered module (Jash's suggested approach). Owners have NOT yet confirmed them - confirm, then change either side.

| ID | Found in | Owner | Test | Finding | Status |
|----|----------|-------|------|---------|--------|
| B001 | data/ | Atharva | `test_our_schema_matches_what_the_modules_require`, `test_sample_files_use_exactly_the_shared_columns` | Sample data used ticker/asset_name/asset_class/avg_buy_price/type and had no portfolio_id; backend returned 422 | Fixed: data regenerated in shared schema, fees dropped |
| B002 | tests/contract.py | Atharva | `NOT_DELIVERED` + `resolve()` failing on missing modules | Missing modules were skipped, so analytics/risk/behaviour showed green while checking nothing | Fixed: only health_score may skip |
| B003 | tests/test_api.py | Atharva | `test_sample_files_upload_returns_200` | Route was /api/analyze; real route is POST /api/portfolio/upload | Fixed and run against the real backend |
| B004 | analytics | Aditya | `test_duplicate_symbols_are_merged_with_warning` | DECISION: duplicates merged + warning (200), not rejected | Awaiting Aditya |
| B005 | analytics | Aditya | `test_zero_quantity_row_is_skipped_with_warning` | DECISION: zero quantity skipped + warning | Awaiting Aditya |
| B006 | analytics | Aditya | `test_zero_current_price_falls_back_to_buy_price_and_is_flagged` | DECISION: zero price -> buy price, price_missing flag + warning | Awaiting Aditya |
| B007 | behavior | Prisha | `test_known_sample_facts`, `test_counts_and_flags_match_oracle` | DECISION: "loss sell" = FIFO match held <=7 days with loss >=5% (not "any sell below avg cost"). Contract keys loss_sell_count/most_traded_ticker replaced by short_hold_loss_sell_count/most_traded_symbol (derived) | Awaiting Prisha |
| B008 | behavior | Prisha | `test_oversell_is_reported_not_rejected`, `test_oversell_transactions_accepted_with_warning` | DECISION: oversell reported as unmatched_sells, not rejected. Confirmed: the API returns 200 | Awaiting Prisha |
| B009 | behavior | Prisha | `test_short_history_has_no_score`, `test_behavior_score_matches_oracle` | Score is null unless >=30 days, >=10 trades, a match, no unmatched sells; now tested | Covered |
| B010 | tests/ | Atharva | pytest collection | tests/test_analytics.py and tests/test_risk.py clashed with Aditya's and Soumil's files | Fixed: renamed *_reference |
| B011 | health score | Jash | `test_health_score.py`, `test_health_score_end_to_end` | Module was not delivered; tests skipped visibly | Resolved: delivered as backend/services/health_score.py; now a required module |
| B012 | backend | Jash | `test_upload_includes_health_score` | Upload response had no health_score | Resolved: xfail marker removed |
| B013 | analytics.validate_portfolio | Aditya | `test_invalid_input_raises_value_error[portfolio_blank_symbol]`, `test_invalid_portfolio_is_rejected_with_422[portfolio_blank_symbol]` | Only on pandas 3 (the project pins 2.3.3, where the module already rejects it): a blank symbol is read as NaN and `astype(str)` keeps it NaN, so the check never fires and the row is analysed. User-visible effect: the API returned a 500 instead of a 422, because the missing symbol crashed the risk engine. Expected: PortfolioDataError / 422 | Fix pending: Aditya's one-line change in analytics/portfolio_metrics.py. Mark Fixed once merged. Our strict xfail marker was removed (it failed on pandas 2.3.3, where the test unexpectedly passes) |
| B014 | backend | Jash | `test_get_routes_return_json_after_upload` | GET after upload returned 500 `no such table: uploads` when the app was used without startup | Resolved: found by our tests, fixed by Jash (tables are created on first use) |
| B015 | tests/ | Atharva | `test_api.py` (upload response keys) | Our API tests assumed `summary` and `upload_id` keys; the real upload response nests analytics under `analytics`, `risk`, `behavior`, `health_score` and identifies the portfolio by `portfolio_id` | Resolved: tests follow the real response |

Run record (real project, clean venv): pandas 2.3.3 -> 310 passed, 0 failed, 0 skipped. pandas 3.0.2 -> same once B013's fix is merged (3 blank-symbol tests, incl. Jash's own `test_blank_symbol_is_rejected`, fail until then).
