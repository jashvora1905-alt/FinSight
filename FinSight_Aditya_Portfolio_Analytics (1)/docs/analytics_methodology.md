# FinSight Portfolio Analytics Methodology — Prototype v1

Owner: Aditya Shah (E062)
Module: `analytics/`
Branch: `feature/portfolio-analytics`

The analytics module answers *what is happening inside the portfolio*: how much was invested, what it is worth now, what has been gained or lost, and how the money is spread across asset types, sectors and stocks. Every calculation is deterministic (same input, same output) and covered by tests. The AI Insight Engine explains these numbers; it never recalculates them.

## 1. Input contract

Portfolio CSV (Project Guide §18):

| Column | Type | Required | Notes |
|---|---|---|---|
| `portfolio_id` | text | yes | Filter with `portfolio_id=` when a file holds several portfolios |
| `symbol` | text | yes | Upper-cased |
| `company_name` | text | yes (column) | Blank → symbol |
| `asset_type` | text | yes (column) | Blank → `Unknown` |
| `sector` | text | yes (column) | Blank → `Unknown` |
| `quantity` | number | yes | Must be ≥ 0 |
| `average_buy_price` | number | yes | Must be > 0 |
| `current_price` | number | yes (column) | Blank/0 → see §4 |

Accepted sources: CSV path, file-like object (e.g. FastAPI `UploadFile.file`) or a pandas DataFrame.

## 2. Formulas (`calculations.py`)

For every holding *i*:

| Metric | Formula |
|---|---|
| Invested value | quantityᵢ × average_buy_priceᵢ |
| Current value | quantityᵢ × current_priceᵢ |
| Absolute P&L | current valueᵢ − invested valueᵢ |
| Return % | (current valueᵢ − invested valueᵢ) / invested valueᵢ × 100 |
| Weight % | current valueᵢ / total current value × 100 |
| Contribution to return % | P&Lᵢ / total invested value × 100 |

Portfolio level: invested value, current value and P&L are sums across holdings; portfolio return % = total P&L / total invested × 100. The contributions of all holdings add up to the portfolio return %, so the dashboard can show which stocks drove the result.

Return % is undefined (`None`) when invested value is 0.

## 3. Allocation (`allocation.py`)

Holdings are grouped by `asset_type`, `sector` and `symbol`. For each group:

- current value, invested value, P&L, return %, number of holdings
- `weight_pct` — share of total **current** value (the main allocation figure)
- `invested_weight_pct` — share of total **invested** value
- `drift_pct` = weight_pct − invested_weight_pct (how far the mix has moved from what was bought, because some holdings grew faster than others)

Groups are sorted largest first. Concentration metrics (largest holding %, top-3 %, HHI) and diversification scoring are owned by the Risk & Diversification module (`risk_engine/`) and are not duplicated here, so the dashboard never shows two versions of the same number. Both modules compute weights the same way, which a test checks.

## 4. Data validation and edge cases (`portfolio_metrics.py`)

| Case | Behaviour |
|---|---|
| Empty file / no rows | `PortfolioDataError` |
| Missing required column | `PortfolioDataError` listing the columns |
| Non-numeric or negative quantity/price | `PortfolioDataError` naming the symbols |
| Missing or zero `average_buy_price` | `PortfolioDataError` (invested value unknown) |
| Quantity = 0 | Row skipped, warning added |
| All quantities 0 | `PortfolioDataError` |
| Missing or zero `current_price` | Average buy price used (P&L = 0 for that holding), `price_missing: true`, warning added |
| Same symbol on several rows | Merged: quantities summed, buy price quantity-weighted, warning added |
| Several portfolios, no filter | Analysed together, warning added |
| Unknown `portfolio_id` | `PortfolioDataError` |
| Single-stock / very large portfolio | Supported (tested with 1 and 500 holdings) |

The backend should turn `PortfolioDataError` into HTTP 422 and show `warnings` on the dashboard.

## 5. Output (`analyze_portfolio()`)

One JSON-serialisable dict. Money is rounded to 2 decimals (₹); percentages are on a 0–100 scale, rounded to 2 decimals.

```
{
  "portfolio_id": "P001",
  "summary": {
    "invested_value", "current_value", "pnl", "return_pct", "status",
    "number_of_holdings", "gainers", "losers", "unchanged",
    "total_gains", "total_losses",
    "top_gainers": [{symbol, return_pct, pnl}],   # up to 3
    "top_losers":  [{symbol, return_pct, pnl}],
    "largest_pnl_contributor": {symbol, return_pct, pnl} | null,
    "largest_pnl_detractor":   {symbol, return_pct, pnl} | null
  },
  "holdings": [{
    "symbol", "company_name", "asset_type", "sector", "quantity",
    "average_buy_price", "current_price", "invested_value", "current_value",
    "pnl", "return_pct", "weight_pct", "contribution_pct", "status", "price_missing"
  }],
  "allocation": {
    "basis": "current_value",
    "by_asset_type": [{name, current_value, invested_value, weight_pct,
                       invested_weight_pct, drift_pct, pnl, return_pct, holdings}],
    "by_sector":     [...same fields...],
    "by_security":   [...same fields...],
    "number_of_asset_types", "number_of_sectors"
  },
  "warnings": []
}
```

These map directly to the API endpoints in Project Guide §17:

| Endpoint | Field |
|---|---|
| `GET /api/portfolio/summary` | `summary` |
| `GET /api/portfolio/holdings` | `holdings` |
| `GET /api/portfolio/performance` | `summary` + per-holding `pnl`, `return_pct`, `contribution_pct` |
| `GET /api/portfolio/allocation` | `allocation` |

## 6. Worked example (sample portfolio P001)

| Symbol | Qty | Avg buy | Current | Invested | Current value | P&L | Return % |
|---|---|---|---|---|---|---|---|
| RELIANCE | 10 | 2,400 | 2,650 | 24,000 | 26,500 | +2,500 | 10.42 |
| TCS | 5 | 3,500 | 4,100 | 17,500 | 20,500 | +3,000 | 17.14 |
| INFY | 8 | 1,500 | 1,650 | 12,000 | 13,200 | +1,200 | 10.00 |
| **Total** | | | | **53,500** | **60,200** | **+6,700** | **12.52** |

Sector allocation: IT = (20,500 + 13,200) / 60,200 = **55.98%**, Energy = 26,500 / 60,200 = **44.02%**.

Contributions: RELIANCE 2,500 / 53,500 = 4.67%, TCS 5.61%, INFY 2.24% → total 12.52% = portfolio return.

These exact values are asserted in `tests/test_analytics.py`.

## 7. Integration

**Backend (Jash)** — suggested usage:

```python
from fastapi import HTTPException, UploadFile
from analytics import analyze_portfolio, PortfolioDataError

def upload(file: UploadFile, portfolio_id: str | None = None):
    try:
        return analyze_portfolio(file.file, portfolio_id=portfolio_id)
    except PortfolioDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

**Risk engine (Soumil)** — the cleaned holdings table can be passed straight in:

```python
from analytics import load_portfolio, compute_holdings
from risk_engine import analyze_portfolio_risk

df, warnings = load_portfolio("data/sample_portfolio.csv")
holdings = compute_holdings(df[df["portfolio_id"] == "P001"])
risk = analyze_portfolio_risk(holdings)
```

**Health Score / AI** — use `summary.return_pct`, `summary.gainers/losers` and `allocation` as structured inputs.

## 8. Assumptions and limitations

- Prices are taken from the CSV; there is no live market data in the prototype (Project Guide §21, Future Scope).
- Return % is a simple (absolute) return since purchase, not annualised (no purchase dates in the portfolio CSV). XIRR/CAGR could be added once transaction dates are combined.
- Dividends, charges and taxes are not included.
- All amounts are assumed to be in one currency (₹).
- Results are informational, not financial advice (Project Guide §25).

## 9. Running the tests

```
python -m pip install -r analytics/requirements.txt
python -m pytest tests/test_analytics.py -v
```

The risk-integration test runs automatically once `risk_engine/` is present (after both branches are merged into `main`) and is skipped otherwise.
