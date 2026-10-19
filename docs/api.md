# FinSight API

Run from the repository root: `python -m uvicorn backend.main:app --reload`. Interactive documentation: `http://127.0.0.1:8000/docs`.
All errors are `{"detail": "<message>"}`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service liveness (not the portfolio health score) |
| `POST` | `/api/portfolio/upload` | Upload CSV files, validate, store and analyse |
| `GET` | `/api/portfolio/summary` | Totals, P&L, return, gainers and losers |
| `GET` | `/api/portfolio/holdings` | Per-holding values, P&L and weights |
| `GET` | `/api/portfolio/performance` | Summary plus per-holding P&L and contribution |
| `GET` | `/api/portfolio/allocation` | Allocation by asset type, sector and security |
| `GET` | `/api/portfolio/risk` | Concentration, risk metrics, risk score |
| `GET` | `/api/portfolio/diversification` | Diversification score, level and gaps |
| `GET` | `/api/portfolio/behavior` | Trading behaviour analysis (404 if no transactions were uploaded) |
| `GET` | `/api/portfolio/health` | Portfolio Health Score with explanation (`health-v2`) |
| `GET` | `/api/portfolio/insights` | AI insights. **501 until the AI module is integrated** |

All `GET /api/portfolio/*` endpoints accept an optional `?portfolio_id=`. Without it they use the portfolio (or portfolios) written by the most recent upload.

## Upload

`multipart/form-data`:

| Field | Required | Notes |
|---|---|---|
| `portfolio` | yes | `.csv`, see `docs/data_dictionary.md` |
| `transactions` | no | `.csv`. A header-only file is treated as not provided |
| `price_history` | no | `.csv` with `date,symbol,close`; enables volatility and maximum drawdown |
| `portfolio_id` | no | Analyse and store only this portfolio from the file |
| `observation_start`, `observation_end` | no | Behaviour window, `YYYY-MM-DD` |

Response: `portfolio_id` (null if several portfolios were analysed together), `portfolio_ids`, `inputs`, `analytics`, `risk`, `behavior` (null without transactions), `health_score`.

**An upload replaces everything stored for each `portfolio_id` it contains** (holdings, transactions and price history), so a stored portfolio always equals its latest upload.
Nothing is stored if validation fails.

```bash
curl -F portfolio=@data/sample_portfolio.csv -F transactions=@data/sample_transactions.csv http://127.0.0.1:8000/api/portfolio/upload
curl http://127.0.0.1:8000/api/portfolio/health
```

## Errors

| Status | When |
|---|---|
| 422 | Invalid or missing data or columns (module validation messages are passed through), empty or non-UTF-8 file, transactions for a portfolio not in the portfolio file |
| 415 | Uploaded file is not `.csv` |
| 413 | A file is larger than 5 MB |
| 404 | Nothing uploaded yet, unknown `portfolio_id`, or no transactions for `/behavior` |
| 405 | Wrong method |
| 501 | `/insights` (AI module not integrated yet) |
| 500 | Unexpected error (details are logged, not returned) |
