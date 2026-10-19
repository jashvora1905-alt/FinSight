# FinSight Architecture

```text
 CSV files ──► POST /api/portfolio/upload ──► validate (analysis modules) ──► SQLite (replace portfolio)
                                                         │
 GET /api/portfolio/* ──► load stored rows ──► analytics ─┬─► risk_engine ─┬─► Health Score engine ──► JSON
                                                          └─► behavior ────┘
```

| Layer | Folder | Owner | Responsibility |
|---|---|---|---|
| API | `backend/api/` | Jash | One router per README entry: `portfolio`, `risk`, `behavior`, `health`, `insights` |
| Schemas | `backend/schemas/` | Jash | Pydantic response models that follow the module output shapes |
| Services | `backend/services/` | Jash | `upload_service` (read, validate, store), `analysis_service` (run the modules), `health_score` (health-v2) |
| Database | `backend/database/`, `backend/models/` | Jash, Atharva | SQLite schema and all SQL |
| Portfolio analytics | `analytics/` | Aditya | Totals, P&L, return, allocation, per-holding performance |
| Risk engine | `risk_engine/` | Soumil | Concentration, diversification, volatility, drawdown, risk score |
| Behaviour engine | `behavior/` | Prisha | Transaction analysis, trading frequency, panic-selling indicator, behaviour score |
| AI engine | `ai/` | Rayyan | Not integrated yet (`/api/portfolio/insights` returns 501) |
| Frontend | `frontend/` | Ricky | Dashboard built against `docs/api.md` |
| Data and tests | `data/`, `tests/` | Atharva | Sample and edge-case data, reference tests, integration tests |

Principles:
- The backend contains no financial calculations beyond the Health Score formula; the modules calculate and the API shapes the output.
- Analysis is always recomputed from the stored rows, so the stored data is the single source of truth.
- Expected failures return `{"detail": ...}` with a 4xx status; unexpected ones return a generic 500 and are logged.
- Run from the repository root so that `analytics`, `risk_engine`, `behavior` and `backend` import as top-level packages.
