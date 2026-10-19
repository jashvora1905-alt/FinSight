# Review notes for Jash (Atharva, data layer co-owner)

## docs/data_dictionary.md and backend/database/connection.py
Checked against the real backend and our sample data. No changes needed.
* Every rule in the Portfolio CSV table is exercised by an edge-case file and passes (negative quantity error,
  zero quantity dropped, zero buy price error, zero current price falls back to cost with `price_missing`,
  duplicate symbols merged, blank portfolio_id/symbol rejected).
* Transactions: duplicate `transaction_id` -> 422, header-only file -> "not provided", unknown portfolio_id -> 422;
  all three have API tests.
* Re-uploading the same files replaces rather than duplicates (test_uploading_twice_replaces_rather_than_duplicates).
* connect() creates tables on first use and reads config.DB_PATH at call time, so tests can point it at a temporary file.
* Optional, not required: transactions has no UNIQUE(portfolio_id, transaction_id); duplicates are rejected in code,
  so the data is safe, but a constraint would protect writes made outside the upload path.

## docs/health_score_methodology.md section 4 (sign-off)
I re-ran the engine on our data. Every number in both section 4 tables reproduces exactly
(component values and the four score columns for the four portfolios). Added tests so it stays true:
* `test_portfolio_ordering_holds_for_every_behaviour_case`: sample > concentrated > single holding for no/poor/sample/good behaviour
* `test_behaviour_ordering_poor_below_sample_below_good`: on all four portfolios
* `test_documented_sample_scores`: pins 69.49 (partial) and 72.43 so a weight change without a doc update fails
Not verified by me: the weight-sensitivity figures (3,000 random draws) and the literature claims in section 3.
Sign-off is for section 4 as reproduced on our sample data.
