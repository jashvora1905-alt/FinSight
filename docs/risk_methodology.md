# FinSight Risk & Diversification Methodology — Prototype v1

Owner: Soumil Patro  
Module: `risk_engine/`  
Branch: `feature/risk`

## Input contract

Minimum holdings columns used by the risk engine:

- `symbol`
- `sector`
- `quantity`
- `current_price`

The full project portfolio format may also include `portfolio_id`, `company_name`, `asset_type`, and `average_buy_price`.

Historical-price input is optional and uses long format:

```csv
date,symbol,close
2026-01-01,RELIANCE,2410.00
2026-01-02,RELIANCE,2432.00
```

## Concentration

Current holding value = `quantity × current_price`.

Holding weight = holding current value / total current portfolio value.

The module reports largest holding %, top-three holdings %, holding HHI, largest sector %, sector HHI, and detailed holding/sector weights.

HHI = sum of squared weights. A higher HHI indicates greater concentration.

## Diversification

The module reports distinct holdings, distinct sectors, effective number of holdings (`1 / holding HHI`), effective number of sectors (`1 / sector HHI`), a prototype diversification score, level, and explicit diversification gaps.

The diversification score is a documented prototype heuristic. It rewards breadth across holdings and sectors and penalizes dominant holdings/sectors. It is not a regulatory or advisory score.

## Historical risk metrics

When usable historical closing prices exist:

- Daily asset return = `P_t / P_(t-1) - 1`
- Portfolio daily return = weighted sum of asset returns
- Annualized volatility = sample standard deviation of daily portfolio returns × `sqrt(252)`
- Drawdown = cumulative portfolio wealth / running peak - 1
- Maximum drawdown = minimum drawdown
- Risk contribution uses the annualized covariance matrix. Component variance contribution for asset i is `w_i × (Σw)_i`; percentage contributions are normalized by total portfolio variance.

When historical data is absent or insufficient, the engine returns these historical metrics as unavailable rather than inventing values.

## Risk Score — Prototype v1

Range: 0–100. Higher means greater measured portfolio risk.

When historical data is available:

- Holding concentration: 25%
- Sector concentration: 20%
- Diversification risk: 15%
- Volatility: 25%
- Maximum drawdown: 15%

When historical data is unavailable, weights are redistributed across deterministic current-portfolio metrics:

- Holding concentration: 40%
- Sector concentration: 35%
- Diversification risk: 25%

Risk levels:

- 0–25: Low
- >25–50: Moderate
- >50–75: High
- >75–100: Very High

Thresholds are transparent prototype assumptions for the academic project, not investment advice.

## Structured output

The main integration function is:

```python
analyze_portfolio_risk(holdings, price_history=None)
```

It returns:

- `portfolio_id`
- `concentration`
- `diversification`
- `risk_metrics`
- `risk_score`
- `limitations`

This structure is intended for the FastAPI backend and Portfolio Health Score Engine.
