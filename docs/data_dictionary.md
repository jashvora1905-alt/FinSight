# FinSight Data Dictionary

## Portfolio CSV (`data/sample_portfolio.csv`)

| Column | Type | Rules |
|---|---|---|
| `portfolio_id` | text | Required on every row, e.g. `P001`. One file may hold several portfolios |
| `symbol` | text | Required. Upper-cased. Duplicate symbols inside a portfolio are merged (quantities summed, buy price quantity-weighted) with a warning |
| `company_name`, `asset_type`, `sector` | text | Blank values get a default |
| `quantity` | number | Negative is an error. Zero: the row is dropped with a warning |
| `average_buy_price` | number | Missing or zero is an error (invested value unknown) |
| `current_price` | number | Missing or zero: the average buy price is used, the holding is flagged `price_missing` and a warning is added |

Source of the rules: `analytics/portfolio_metrics.py` and `docs/analytics_methodology.md`.

## Transactions CSV (`data/sample_transactions.csv`)

`transaction_id, portfolio_id, date (YYYY-MM-DD), symbol, transaction_type (BUY | SELL), quantity, price`.
The behaviour score is available only with at least 30 calendar days and at least 10 transactions; otherwise the response says `insufficient_data`
and lists the reasons. Details: `docs/behavior_methodology.md`.

## Price history CSV (optional)

`date, symbol, close` (long format). Used by the risk engine for volatility and maximum drawdown. The README does not define a format for this; it follows `docs/risk_methodology.md`.

## Database (SQLite, `backend/database/connection.py`)

Tables follow the README "Database Structure". Additions are marked.

| Table | Columns |
|---|---|
| `users` | `id`, `name`, `email`, `created_at` (unused: the prototype has no login) |
| `portfolios` | `id` (TEXT, the CSV `portfolio_id`), `user_id`, `name`, `created_at`, plus `observation_start`, `observation_end` (addition) |
| `holdings` | `id`, `portfolio_id`, `symbol`, `company_name`, `asset_type`, `sector`, `quantity`, `average_buy_price`, `current_price` |
| `transactions` | `id`, `portfolio_id`, `date`, `symbol`, `transaction_type`, `quantity`, `price`, plus `transaction_id` (addition: the CSV id) |
| `price_history` (addition) | `id`, `portfolio_id`, `date`, `symbol`, `close` |

The uploaded rows are stored as uploaded, so re-analysing them gives exactly the upload's result, warnings included.
The README's future tables (`analysis_results`, `health_scores`, `user_preferences`) are not implemented.
