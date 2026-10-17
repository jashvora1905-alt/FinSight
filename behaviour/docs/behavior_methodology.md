# FinSight behaviour module - Prisha Mistry

This is the standalone implementation of the Behaviour Analysis assignment.
It needs Python 3.10 or later and only the Python standard library. No API key,
market-data service, database, Pandas installation or running backend is needed.
The functions also accept `df.to_dict('records')` from a Pandas DataFrame.

## Files and ownership

| File | Responsibility |
| --- | --- |
| `behavior/transaction_analysis.py` | CSV input, validation, buy/sell summaries, FIFO holdings |
| `behavior/trading_frequency.py` | Daily activity and high-activity proxy |
| `behavior/panic_selling.py` | Short-hold loss-selling proxy |
| `behavior/behavior_score.py` | Public entry point, component penalties and score |
| `behavior/__main__.py` | Command-line demo |
| `behavior/tests/test_behavior.py` | Module-specific controlled tests |
| `behavior/examples/transactions.csv` | Fictional demo transactions |

Tests and examples stay inside `behavior/` to avoid changing Atharva's working
folders. No frontend, backend, AI or risk-engine files are changed.

## Run the demo

Open a terminal at the FinSight repository root:

```bash
python -m behavior behavior/examples/transactions.csv --portfolio-id P001 --observation-end 2026-01-30
```

On Windows, use `py` instead of `python` if needed. To save a local result:

```bash
python -m behavior behavior/examples/transactions.csv --portfolio-id P001 --observation-end 2026-01-30 > behavior_result.json
```

The sample has six purchases on January 1 and four sales on January 8. Expected:

- Total trades: 10; buys: 6; sells: 4.
- Buy value: 600; sell value: 380, in the input's currency.
- Calendar observation days: 30; active days: 2.
- Trades per calendar day: 0.3333; trades per active day: 5.
- High-activity days: January 1 (6 transactions exceeds the default 5).
- Four closed units held for 7 days, sold at a 5% loss; two units remain open.
- Activity penalty: 25; short-hold loss penalty: 50; experimental score: 25/100.

## Input contract

Required fields:

```text
transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price
```

Dates must be `YYYY-MM-DD`. Quantity and price must be finite, positive numbers.
BUY and SELL are the only supported transaction types. Whitespace is stripped
from identifiers and symbols; symbols and transaction types are uppercased.
Transaction IDs must be unique within a portfolio. Distinct IDs on otherwise
identical rows are treated as distinct trades: the module cannot know whether
they represent duplicate uploads or separate executions.

The public entry point validates all supplied records, including records outside
the selected portfolio. Invalid rows raise `ValueError`; none are silently dropped.
Provide `portfolio_id` for multi-portfolio input. No position matching crosses
portfolio or symbol boundaries. Input records are not mutated.

Dates are sorted chronologically. Equal-date rows preserve input order. The
caller should supply records in execution order within each date; the schema has
no timestamps, so intraday order cannot be independently verified.

## Metrics

- Buy/sell counts and percentages count transactions, not units.
- Transaction value = quantity multiplied by execution price.
- Calendar days = end date minus start date plus one.
- Trades per calendar day = total trades / calendar days.
- Trades per active day = total trades / distinct transaction dates.
- Per-symbol buy/sell counts and per-date trade counts are included.

Observation dates default to first and last selected transaction dates. Optional
explicit boundaries must contain every selected transaction and may extend the
window to include known inactivity. They are not filters. The caller is
responsible for supplying a complete history for those dates; no missing-data
or completeness inference is possible. Do not supply an observation start that
excludes earlier buys needed for holding analysis.

## Holding analysis

FIFO matches each sale with the oldest available purchase of the same symbol.
Partial sales and multiple purchase lots are supported. Decimal arithmetic is
used for matching fractional quantities. Closed holding days = sale date minus
purchase date. The mean closed holding period is weighted by matched quantity.
Each open purchase lot has its remaining quantity and age at observation end.

Sales without sufficient earlier purchases are reported as unmatched. Their
holding durations are unknown; they do not consume future purchases. A partially
matched sale still contributes its known matched portion to the raw metrics.
No opening inventory is invented.

## Prototype indicator rules

These thresholds are implementation assumptions because the guides do not
specify formulas. They require team review and are not validated financial rules.

| Indicator | Default rule | Public keyword |
| --- | --- | --- |
| High activity / overtrading proxy | More than 5 transactions on one date | `daily_trade_threshold=5` |
| Short holding | FIFO-matched sale held for at most 7 calendar days | `max_holding_days=7` |
| Loss threshold | Sale return at or below -5% | `minimum_loss_percentage=5` |

The panic-selling proxy flags matched lot portions satisfying both the short-hold
and loss rules. A sale can have flagged and unflagged portions. Its identifier is
counted once in `flagged_sell_count`. A tiny numerical tolerance of 1e-10
percentage points is used at the loss threshold.

This proxy cannot establish panic, emotional state, an irrational decision, or a
reaction to a market crash. No daily market history or investor strategy is
available. A loss sale can be deliberate. With no matched sales, the indicator is
unavailable (`null`), rather than a negative finding.

## Behaviour score version behavior-v1

Let A = flagged active days / all active days.
Let L = flagged matched quantity / all matched sold quantity.

```text
activity_penalty = 50 * A
short_hold_loss_penalty = 50 * L
score = max(0, min(100, 100 - activity_penalty - short_hold_loss_penalty))
```

The final score is rounded to two decimal places. The equal weights are fixed
version-1 prototype choices. Thresholds can be changed through function keywords.

A score is available only with all of:

- At least 30 calendar days of observation.
- At least 10 transactions.
- At least one FIFO-matched purchase/sale portion.
- No unmatched sales in the history.

Otherwise `behavior_score.value` is `null` and `reasons` explains why. These
minimum-data rules are also prototype assumptions. Buy-only and empty histories
do not automatically receive a perfect score. Even an available score is not a
validated assessment of investment skill, emotional health or future returns.
Quantity weighting across different symbols is sensitive to share denominations
and stock splits; this is an explicit limitation of version 1.

No short sales, fees, splits, dividends, other corporate actions, investment
objectives or external cash flows are modeled. Supply consistently adjusted
history where applicable. Inputs are assumed to use one currency; there is no
currency conversion. Extreme values producing non-finite derived metrics fail
with `ValueError` rather than emitting invalid JSON numbers.

## Backend, Health Score and AI handoff

Jash can call the public function from the backend service:

```python
from behavior import analyze_behavior, load_transactions

records = load_transactions("path/to/transactions.csv")
result = analyze_behavior(
    records,
    portfolio_id="P001",
    observation_start="2026-01-01",
    observation_end="2026-01-30",
)
```

Or pass database records as a list of dictionaries. Convert database date objects
to ISO strings before calling. For DataFrames use `df.to_dict('records')`.

The dictionary contains:

| Key | Consumer use |
| --- | --- |
| `methodology_version` | Identify scoring rules and output contract |
| `portfolio_id`, `status` | Identify portfolio and overall data availability |
| `summary` | Counts, transaction values, per-symbol activity |
| `frequency` | Calendar window, activity counts and overtrading proxy |
| `holdings` | Matched lots, closed durations, open lots and unmatched sales |
| `panic_selling_indicator` | Rule flags, matched portions and limitations |
| `behavior_score` | Value, availability, formula, penalties and reasons |
| `warnings` | Limitations to preserve in interpretation |

`status=available` means raw metrics exist; inspect
`behavior_score.status` separately before using the score. For empty input without
both observation dates, frequency, holdings and panic-selling fields are `null`.
With an explicit empty observation window, frequency metrics exist but the score
and panic-selling assessment remain unavailable.

The Health Score Engine must preserve unavailable values or explicitly reweight
other components; it must not silently substitute zero or 100. Rayyan's AI should
explain these results and limitations without independently recalculating them.
The module contains no FastAPI routes: Jash owns the eventual
`GET /api/portfolio/behavior` endpoint and HTTP error mapping.

## Verify

```bash
python -m unittest discover -s behavior/tests -v
```

The suite covers known numerical answers, FIFO matching, fractional quantities,
partial/unmatched sales, threshold boundaries, calendar denominators, score
eligibility, portfolio isolation, date sorting, invalid input, duplicate IDs,
CSV parsing and input immutability.

## Add to your Git branch

Copy `behavior/` and `docs/behavior_methodology.md` into your local FinSight clone.
If `feature/behavior` does not exist yet:

```bash
git checkout main
git pull origin main
git checkout -b feature/behavior
python -m unittest discover -s behavior/tests -v
git add behavior docs/behavior_methodology.md
git commit -m "Add deterministic behaviour analysis and prototype scoring"
git push -u origin feature/behavior
```

If the branch already exists locally, use `git checkout feature/behavior` instead
of `git checkout -b feature/behavior`. Open a pull request into `main` after
pushing. Share the module interface and methodology with Jash, Rayyan and Atharva
for integration. The complete FinSight application still requires their modules.
