# FinSight Health Score: Methodology `health-v2`

Owner: Jash (Backend) · Coordination with Aditya (analytics), Soumil (risk), Prisha (behaviour) · Code: `backend/services/health_score.py`

The README defines the Health Score as the combination of four dimensions: **Performance, Risk, Diversification and Behaviour**.
This document defines how each dimension is scored, how they are combined, and what the evidence and limits are.
It is informational only and not financial advice.

## 1. Formula

Every component is on a 0 to 100 scale where higher means healthier.

| Component | Value | Source |
|---|---|---|
| Performance | `clamp(50 + 50 × return_pct / 30, 0, 100)` | `analytics` `summary.return_pct` (return since purchase, not annualised) |
| Risk | `100 − risk_ex` | `risk_engine` `risk_score.components` and `component_weights`, **excluding** `diversification_risk`, re-weighted to sum to 1 |
| Diversification | `diversification_score` | `risk_engine` `diversification.diversification_score` |
| Behaviour | `behavior_score.value` | `behavior`, used only when `status == "available"` |

Base weights: **Risk 0.35 · Diversification 0.25 · Behaviour 0.25 · Performance 0.15.**

```
applied_weight(c) = base_weight(c) / sum(base weights of the components that are available)
score             = sum(applied_weight(c) × value(c))
points_lost(c)    = applied_weight(c) × (100 − value(c))        so   score = 100 − sum(points_lost)
```

Bands (same cut-offs as the risk levels, inverted): **≥ 75 Strong · ≥ 50 Moderate · ≥ 25 Weak · below 25 Poor.**

Arithmetic uses exact decimals with half-up rounding to 2 decimal places, so results are reproducible.

### Missing components
A component that cannot be measured (no transactions, fewer than 30 days or 10 transactions, no return) is **never replaced by an invented value**.
The remaining weights are rescaled, `score_basis` becomes `"partial"`, `coverage` falls below 1 (the share of the full model that was scored)
and `missing_components` lists what is absent. The dashboard should show a partial score as provisional.
Risk and Diversification are always available.

### Output (`GET /api/portfolio/health`)
`score`, `band`, `score_basis` (`full` | `partial`), `coverage`, `missing_components`, `components` (per component: `value`, `base_weight`,
`weight_applied`, `available`, `status`, `contribution_points`, `points_lost`, `source`), `explanation` and `methodology_version`.
`explanation` is the README's "score explanation": `summary` (one sentence naming the largest drag), `drivers` (components ranked by points lost)
and `notes` (provisional-score reasons, the behaviour module's own reasons, diversification gaps, missing price history, holdings priced at cost).

## 2. Design decisions

| Decision | Reason |
|---|---|
| Risk excludes `diversification_risk` | Soumil's `risk_score` already contains diversification (25% of it, 15% with price history). Using his full score plus the diversification score would count diversification twice. Concentration still appears in both components, because his diversification score contains concentration terms (45 of its 100 points). This overlap is inherent to his module and is declared here. |
| Linear weighted sum of normalised components | The standard composite-indicator method (OECD/EU-JRC handbook): normalise, weight, aggregate, test sensitivity. Its known limit is that strong components can offset weak ones. |
| Weights are a judgement | No source gives correct weights. Structural measures (Risk, Diversification) are always available and have the strongest evidence, so they carry 0.60 together. Behaviour is supported by research but its rules are unvalidated proxies, so 0.25. Performance is descriptive, weakly predictive and its scale is an assumption, so 0.15. |
| Performance scale ±30% | Return since purchase of −30% maps to 0, 0% to 50, +30% or more to 100. The −30% anchor is the roughly 30% fall of the Indian equity market in early 2020 reported by Raju & Agarwalla (2021). The +30% cap stops large gains from being rewarded without limit. This scale is an assumption; sensitivity is shown below. |
| Missing = rescale and flag | Prisha's methodology requires that the Health Score must not silently use 0 or 100 for an unavailable behaviour score. |

## 3. Evidence and sources

| Claim used | Source | What was read |
|---|---|---|
| Composite scores: normalise, weight, aggregate, test sensitivity | OECD/EU-JRC, *Handbook on Constructing Composite Indicators* (2008). https://knowledge4policy.ec.europa.eu/sites/default/files/jrc47008_handbook_final.pdf | Contents and OECD applications of it, not the full text |
| More holdings reduce diversifiable risk; no consensus on how many | Statman (1987), *Journal of Financial and Quantitative Analysis* 22(3). https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/how-many-stocks-make-a-diversified-portfolio/CE5CDF2C7225FC1E0EDE3E700A3C66A7 | Abstract |
| Same question on Indian stocks, equity-market fall of about 30% in early 2020, volatility levels | Raju & Agarwalla (2021), IIM Ahmedabad Working Paper 2021-02-02. https://www.iima.ac.in/sites/default/files/rnpfiles/8646889802021-02-02.pdf | Full paper |
| Frequent trading hurts individual investors | Barber & Odean (2000), *Journal of Finance* 55(2). https://ideas.repec.org/a/bla/jfinan/v55y2000i2p773-806.html | Abstract |
| Past performance is weakly persistent | Carhart (1997); Choi & Zhao, NBER w26707. https://www.nber.org/papers/w26707.pdf | Abstracts and summaries |
| 10% single-issuer and 25% single-sector limits (analogy) | SEBI mutual-fund rules for **debt** schemes. https://www.business-standard.com/article/pti-stories/sebi-notifies-stricter-mf-norms-reduces-single-issuer-limit-116021500354_1.html | News summaries. No equivalent rule was verified for equity, and nothing regulates an individual's portfolio. |

## 4. Validation (real module outputs on `data/`)

Component values on the sample portfolios (no transactions):

| Portfolio | Performance | Risk | Diversification | Return since purchase |
|---|---|---|---|---|
| Sample (12 holdings) | 69.33 | 61.34 | 80.98 | 11.6% |
| All losses | 12.93 | 11.29 | 20.44 | −22.24% |
| Concentrated | 80.12 | 0.00 | 24.00 | 18.07% |
| Single holding | 67.68 | 0.00 | 8.00 | 10.61% |

Health score. `*` marks a partial score (behaviour not scored). Behaviour columns: poor = every matched sale was a short-hold loss (B = 50), sample = `data/sample_transactions.csv` (B = 81.25), good = profitable long holds (B = 100).

| Portfolio | No transactions | Poor | Sample | Good |
|---|---|---|---|---|
| Sample | 69.49 * | 64.62 | 72.43 | 77.12 |
| All losses | 14.67 * | 23.50 | 31.32 | 36.00 |
| Concentrated | 24.02 * | 30.52 | 38.33 | 43.02 |
| Single holding | 16.20 * | 24.65 | 32.47 | 37.15 |

- Diversified scores above concentrated, which scores above single holding, for every behaviour case, as Atharva's tests require.
- On the same portfolio, poor behaviour scores below sample behaviour, which scores below good behaviour.
- **Weight sensitivity** (3,000 random weight sets drawn around the base weights): the portfolio ordering held in 100% of draws; the sample portfolio's score ranged 69.0 to 75.5 (5th to 95th percentile) and its band was unchanged in 91% of draws. Bands near a cut-off can flip.
- **Performance scale sensitivity:** ±20% / ±30% / ±40% gives 73.88 / 72.43 / 71.70 for the sample portfolio.
- **Double-count check:** on the sample portfolio, `100 − risk_score` would be 66.25, while the Risk component is 61.34, because diversification is scored separately.

## 5. Limitations

- Weights, the performance scale and several thresholds inside the modules are documented prototype assumptions, not estimated values. The structure is sourced; the numbers are partly judgement.
- A partial score cannot be compared directly with a full one. A blend can raise the score when the missing component would have been lower than the others: for the concentrated portfolio, no transactions gives 24.02 but poor behaviour gives 30.52.
- Performance rewards a gain even on a concentrated portfolio (the concentrated sample scores 80.12 on Performance). Its weight is kept small for this reason.
- Return is measured since purchase, not annualised, because holding periods are unknown.
- Soumil's breadth score gives full marks at 10 holdings, the low end of the research range (Statman suggests 30 to 40; the Indian evidence suggests about 85% of diversifiable risk is removed at 10 stocks and 92% at 20), and counts an ETF or fund as one holding.
- Prisha's thresholds (more than 5 trades a day; a loss of at least 5% within 7 days) have no direct empirical anchor.
- Diversification evidence is for equities and equal-weighted random portfolios. No live prices, dividends, fees or taxes are used.
