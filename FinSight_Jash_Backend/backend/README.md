# FinSight Backend (Jash Vora, `feature/backend`)

FastAPI service that accepts CSV uploads and integrates the analytics (Aditya), risk (Soumil) and behaviour (Prisha) modules.
It contains **no financial calculations** – it validates input, calls the modules, stores the upload in SQLite and shapes the JSON.

## Run (from the repository root, next to `analytics/`, `risk_engine/`, `behavior/`)
```
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload          # http://127.0.0.1:8000/docs for the interactive API docs
python -m pytest backend/tests -q          # backend tests
```
Env vars (optional): `FINSIGHT_DB` (SQLite path, default `backend/finsight.db`), `FINSIGHT_CORS_ORIGINS` (default Vite: `http://localhost:5173,http://127.0.0.1:5173`).

## Endpoints
| Method & path | Purpose |
|---|---|
| `GET /health` | liveness |
| `POST /api/upload` | multipart: `portfolio` (required .csv), `transactions`, `price_history` (optional .csv); form fields `portfolio_id`, `observation_start`, `observation_end` (optional). Validates, runs all modules, stores the upload, returns `{upload_id, portfolio_id, inputs, analytics, risk, behavior, health_score}` |
| `GET /api/portfolio/summary` · `/holdings` · `/performance` · `/allocation` | Aditya's `summary`, `holdings`, summary + per-holding P&L/contribution, `allocation` |
| `GET /api/portfolio/risk` | Soumil's `analyze_portfolio_risk` output |
| `GET /api/portfolio/health-score` | Health Score (`health-v1`, see below) |
| `GET /api/portfolio/behavior` | Prisha's `analyze_behavior` output (404 if no transactions were uploaded) |

All GET endpoints take an optional `?upload_id=` (default: most recent upload). `upload_id` is a hash of the inputs, so identical uploads give identical responses.

## Input schemas (as the modules require them – Project Guide §18)
- Portfolio: `portfolio_id, symbol, company_name, asset_type, sector, quantity, average_buy_price, current_price`
- Transactions: `transaction_id, portfolio_id, date (YYYY-MM-DD), symbol, transaction_type (BUY/SELL), quantity, price`
- Price history (optional): `date, symbol, close`

## Errors – always `{"detail": "<message>"}`
`422` invalid/missing data or columns (module validation messages are passed through) · `415` not a `.csv` · `413` file > 5 MB ·
`404` nothing uploaded / unknown `upload_id` / no transactions · `405` wrong method · `500` unexpected (details logged, not returned).
Bad uploads are never stored.

## Health Score (`backend/health_score.py`, methodology `health-v1`)
```
R = 100 - risk_score.score          (risk_engine)        B = behavior_score.value   (behavior, only if status == "available")
score = 0.70*R + 0.30*B             -> score_basis "full",      coverage 1.00
score = R                           -> score_basis "risk_only", coverage 0.70   (behaviour unavailable: explicit reweighting, flagged as provisional)
band:  >=75 Strong · >=50 Moderate · >=25 Weak · else Poor      (aligned with risk_engine levels)
```
Past returns are not scored; diversification is not added separately (risk_score already contains it). Exact decimal arithmetic, half-up rounding to 2 dp.
Python entry points: `compute_health_score(risk, behavior=None)` (pure formula, used by the API) and
`calculate_health_score(portfolio_df, transactions_df=None, portfolio_id=None)` (DataFrame entry point; the signature the test contract expects).
Rationale, sources and validation: "FinSight Health Score: Methodology v1" (Claude Doc). Informational only, not financial advice.

## Not included yet
AI insights: Rayyan's module has not been delivered, so no endpoint or field exists for it.
