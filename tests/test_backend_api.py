"""Backend API + SQLite storage (README: API Structure, Database Structure)."""
import sqlite3

import pytest

from backend import config
from backend.services import analysis_service

from tests.backend_support import (PORTFOLIO, PRICE_HISTORY, QUIRKY, TWO_PORTFOLIOS, available_transactions,  # noqa: F401
                              client, csv_file, make_transactions, post)

README_ROUTES = [
    ("post", "/api/portfolio/upload"), ("get", "/api/portfolio/summary"), ("get", "/api/portfolio/holdings"),
    ("get", "/api/portfolio/performance"), ("get", "/api/portfolio/allocation"), ("get", "/api/portfolio/risk"),
    ("get", "/api/portfolio/diversification"), ("get", "/api/portfolio/behavior"), ("get", "/api/portfolio/health"),
    ("get", "/api/portfolio/insights"),
]
GET_PATHS = ["summary", "holdings", "performance", "allocation", "risk", "diversification", "behavior", "health"]


# ---------- liveness, routes ----------

def test_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_every_readme_route_exists_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    for method, path in README_ROUTES:
        assert method in paths.get(path, {}), f"{method.upper()} {path} missing"


def test_insights_is_an_explicit_501_until_the_ai_module_is_integrated(client):
    r = client.get("/api/portfolio/insights")
    assert r.status_code == 501 and "AI" in r.json()["detail"]


# ---------- upload: happy paths ----------

def test_upload_matches_documented_worked_example(post):
    r = post()
    assert r.status_code == 200, r.text
    body = r.json()
    s = body["analytics"]["summary"]
    # analytics_methodology.md worked example
    assert (s["invested_value"], s["current_value"], s["pnl"], s["return_pct"]) == (53500.0, 60200.0, 6700.0, 12.52)
    assert body["portfolio_id"] == "P001" and body["portfolio_ids"] == ["P001"]
    assert body["behavior"] is None
    assert body["inputs"] == {"transactions_provided": False, "price_history_provided": False}
    assert 0 <= body["risk"]["risk_score"]["score"] <= 100
    assert body["risk"]["risk_metrics"]["historical_data_available"] is False
    assert {x["name"]: x["weight_pct"] for x in body["analytics"]["allocation"]["by_sector"]} == {"IT": 55.98, "Energy": 44.02}


def test_upload_with_transactions_includes_behavior(post):
    b = post(transactions=make_transactions()).json()["behavior"]
    assert b["methodology_version"] == "behavior-v1" and b["summary"]["total_trades"] == 12


def test_upload_with_price_history_enables_historical_risk(post):
    body = post(price_history=PRICE_HISTORY).json()
    assert body["inputs"]["price_history_provided"] is True
    assert body["risk"]["risk_metrics"]["historical_data_available"] is True


def test_unusable_price_history_is_reported_by_risk_engine_not_rejected(post):
    r = post(price_history="when,what\n1,2\n")
    rm = r.json()["risk"]["risk_metrics"]
    assert r.status_code == 200 and rm["historical_data_available"] is False and "price columns" in rm["reason"]


def test_same_input_same_output(post):
    assert post(transactions=make_transactions()).json() == post(transactions=make_transactions()).json()


def test_header_only_transactions_file_is_treated_as_not_provided(post):
    r = post(transactions="transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price\n")
    assert r.status_code == 200 and r.json()["behavior"] is None and r.json()["inputs"]["transactions_provided"] is False


# ---------- stored data == uploaded data (parity) ----------

@pytest.mark.parametrize("kwargs", [
    {}, {"portfolio": QUIRKY}, {"transactions": available_transactions()},
    {"transactions": make_transactions(), "price_history": PRICE_HISTORY},
    {"portfolio": TWO_PORTFOLIOS}, {"portfolio": TWO_PORTFOLIOS, "portfolio_id": "P002"},
], ids=["basic", "quirky-loader-rules", "with-transactions", "tx+prices", "two-portfolios-combined", "one-of-two"])
def test_stored_data_reproduces_the_upload_analysis_exactly(client, post, kwargs):
    up = post(**kwargs).json()
    again = analysis_service.analysis_for(None)           # re-analysed purely from SQLite rows
    for key in ("analytics", "risk", "behavior", "health_score"):
        assert again[key] == up[key], key                 # includes analytics warnings


def test_get_endpoints_return_the_upload_results(client, post):
    up = post(transactions=available_transactions()).json()
    assert client.get("/api/portfolio/summary").json() == up["analytics"]["summary"]
    assert client.get("/api/portfolio/holdings").json() == up["analytics"]["holdings"]
    assert client.get("/api/portfolio/allocation").json() == up["analytics"]["allocation"]
    assert client.get("/api/portfolio/risk").json() == up["risk"]
    assert client.get("/api/portfolio/diversification").json() == up["risk"]["diversification"]
    assert client.get("/api/portfolio/behavior").json() == up["behavior"]
    assert client.get("/api/portfolio/health").json() == up["health_score"]
    perf = client.get("/api/portfolio/performance").json()
    assert perf["summary"] == up["analytics"]["summary"]
    assert {h["symbol"] for h in perf["holdings"]} == {"RELIANCE", "TCS", "INFY"}
    assert round(sum(h["contribution_pct"] for h in perf["holdings"]), 1) == 12.5


def test_get_before_any_upload_is_404(client):
    for path in GET_PATHS:
        r = client.get(f"/api/portfolio/{path}")
        assert r.status_code == 404 and "upload" in r.json()["detail"].lower(), path


def test_behavior_get_without_transactions_is_404(client, post):
    post()
    r = client.get("/api/portfolio/behavior")
    assert r.status_code == 404 and "transactions" in r.json()["detail"].lower()


# ---------- portfolio selection, latest-upload default, replace semantics ----------

def test_portfolio_id_query_selects_a_stored_portfolio(client, post):
    post(TWO_PORTFOLIOS)
    assert client.get("/api/portfolio/summary", params={"portfolio_id": "P001"}).json()["number_of_holdings"] == 3
    assert client.get("/api/portfolio/summary", params={"portfolio_id": "P002"}).json()["number_of_holdings"] == 1
    assert client.get("/api/portfolio/summary").json()["number_of_holdings"] == 4        # latest upload = both, combined


def test_unknown_portfolio_id_is_404_on_get(client, post):
    post()
    r = client.get("/api/portfolio/summary", params={"portfolio_id": "NOPE"})
    assert r.status_code == 404 and "NOPE" in r.json()["detail"]


def test_default_is_the_most_recent_upload_and_older_portfolios_stay_available(client, post):
    post(TWO_PORTFOLIOS)
    post(PORTFOLIO.replace("P001", "P009"))
    assert client.get("/api/portfolio/summary").json()["number_of_holdings"] == 3          # P009
    assert client.get("/api/portfolio/summary", params={"portfolio_id": "P002"}).status_code == 200


def test_reupload_replaces_holdings_transactions_and_price_history(client, post):
    post(TWO_PORTFOLIOS, transactions=available_transactions(), price_history=PRICE_HISTORY, portfolio_id="P001")
    post(PORTFOLIO.replace("RELIANCE,Reliance Industries,Equity,Energy,10", "RELIANCE,Reliance Industries,Equity,Energy,99"))
    conn = sqlite3.connect(config.DB_PATH)
    assert conn.execute("SELECT COUNT(*) FROM holdings WHERE portfolio_id='P001'").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0           # old history gone with the replace
    assert conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0] == 0
    assert conn.execute("SELECT quantity FROM holdings WHERE symbol='RELIANCE'").fetchone()[0] == 99
    assert client.get("/api/portfolio/behavior").status_code == 404


def test_form_portfolio_id_stores_and_analyses_only_that_portfolio(client, post):
    r = post(TWO_PORTFOLIOS, portfolio_id="P002")
    assert r.status_code == 200 and r.json()["portfolio_id"] == "P002" and r.json()["portfolio_ids"] == ["P002"]
    assert client.get("/api/portfolio/summary", params={"portfolio_id": "P001"}).status_code == 404


def test_multiple_portfolios_without_id_are_analysed_together_with_a_warning(post):
    body = post(TWO_PORTFOLIOS).json()
    assert body["portfolio_id"] is None and body["portfolio_ids"] == ["P001", "P002"]
    assert body["analytics"]["summary"]["number_of_holdings"] == 4 and body["analytics"]["warnings"]


def test_unknown_form_portfolio_id_is_422(post):
    r = post(portfolio_id="NOPE")
    assert r.status_code == 422 and "NOPE" in r.json()["detail"]


def test_transactions_for_a_different_portfolio_are_rejected(post):
    r = post(transactions=make_transactions("P009"))
    assert r.status_code == 422 and "P009" in r.json()["detail"]


def test_multiple_portfolios_in_transactions_need_portfolio_id(client, post):
    tx = make_transactions("P001") + make_transactions("P002").split("\n", 1)[1]
    r = post(transactions=tx)
    assert r.status_code == 422 and "portfolio_id" in r.json()["detail"]
    ok = post(transactions=tx, portfolio_id="P001")
    assert ok.status_code == 200
    conn = sqlite3.connect(config.DB_PATH)
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 12          # only P001's rows stored


def test_observation_window_is_used_and_persisted(client, post):
    post(transactions=make_transactions(), observation_start="2026-01-01", observation_end="2026-03-01")
    freq = client.get("/api/portfolio/behavior").json()["frequency"]
    assert (freq["observation_start"], freq["observation_end"]) == ("2026-01-01", "2026-03-01")


def test_bad_observation_date_is_422(post):
    assert post(transactions=make_transactions(), observation_end="01/03/2026").status_code == 422


# ---------- database structure follows the README ----------

def test_database_has_the_readme_tables_and_columns(client, post):
    post()
    conn = sqlite3.connect(config.DB_PATH)
    cols = lambda t: [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
    assert {"users", "portfolios", "holdings", "transactions"} <= {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert cols("users")[:3] == ["id", "name", "email"] and "created_at" in cols("users")
    assert {"id", "user_id", "name", "created_at"} <= set(cols("portfolios"))
    assert cols("holdings")[:9] == ["id", "portfolio_id", "symbol", "company_name", "asset_type", "sector", "quantity", "average_buy_price", "current_price"]
    assert {"id", "portfolio_id", "date", "symbol", "transaction_type", "quantity", "price"} <= set(cols("transactions"))


def test_foreign_keys_cascade_on_delete(client, post):
    post(transactions=available_transactions())
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM portfolios WHERE id='P001'")
    assert conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0


# ---------- invalid input is rejected cleanly (never a 500) ----------

def _bad(post, **kw):
    r = post(**kw)
    assert r.status_code in (400, 413, 415, 422), (r.status_code, r.text)
    assert isinstance(r.json()["detail"], str) and r.json()["detail"]
    return r


def test_missing_portfolio_file(post):
    assert post(portfolio=None).status_code == 422


def test_empty_and_header_only_files(post):
    assert "empty" in _bad(post, portfolio="").json()["detail"].lower()
    _bad(post, portfolio=PORTFOLIO.splitlines()[0] + "\n")


def test_missing_required_column(post):
    assert "Missing required columns" in _bad(post, portfolio="portfolio_id,symbol,quantity\nP001,TCS,5\n").json()["detail"]


def test_non_numeric_and_negative_values(post):
    _bad(post, portfolio=PORTFOLIO.replace(",10,2400,", ",abc,2400,"))
    _bad(post, portfolio=PORTFOLIO.replace(",10,2400,", ",-10,2400,"))


def test_blank_symbol_is_rejected(post):
    _bad(post, portfolio=PORTFOLIO.replace("RELIANCE", ""))


def test_blank_portfolio_id_is_rejected(post):
    assert "portfolio_id" in _bad(post, portfolio=PORTFOLIO.replace("P001,RELIANCE", ",RELIANCE")).json()["detail"]


def test_non_csv_extension_is_415(client):
    assert client.post("/api/portfolio/upload", files={"portfolio": ("notes.txt", b"hello", "text/plain")}).status_code == 415


def test_non_utf8_file(client):
    r = client.post("/api/portfolio/upload", files={"portfolio": ("p.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert r.status_code == 422 and "UTF-8" in r.json()["detail"]


def test_too_large_file(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 50)
    assert client.post("/api/portfolio/upload", files={"portfolio": csv_file(PORTFOLIO)}).status_code == 413


def test_transactions_missing_columns(post):
    r = _bad(post, transactions="transaction_id,date,ticker,type,quantity,price,fees\nT1,2024-01-10,TCS,BUY,1,1,0\n")
    assert "missing columns" in r.json()["detail"].lower()


@pytest.mark.parametrize("mutate", [
    lambda t: t.replace("BUY", "HOLD", 1), lambda t: t.replace("2026-01-01", "not-a-date", 1), lambda t: t.replace(",100\n", ",-5\n", 1)])
def test_invalid_transaction_rows(post, mutate):
    _bad(post, transactions=mutate(make_transactions()))


def test_bad_upload_is_not_stored(client, post):
    post(portfolio="portfolio_id,symbol\nP001,TCS\n")
    post(transactions=make_transactions("P009"))
    assert client.get("/api/portfolio/summary").status_code == 404


def test_wrong_methods_and_unknown_routes(client):
    assert client.get("/api/portfolio/upload").status_code == 405
    assert client.post("/health").status_code == 405
    assert client.get("/api/nope").status_code == 404


def test_unexpected_error_returns_clean_500(client, post, monkeypatch):
    monkeypatch.setattr(analysis_service, "analyze_portfolio", lambda *a, **k: 1 / 0)
    r = post()
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error."}


def test_cors_header_for_vite_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_works_without_app_startup_lifespan(tmp_path, monkeypatch):
    """TestClient(app) used WITHOUT `with` never runs the lifespan; tables must still be created on demand."""
    from fastapi.testclient import TestClient

    from backend.main import app
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "nolifespan.db")
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/api/portfolio/summary").status_code == 404
    assert c.post("/api/portfolio/upload", files={"portfolio": csv_file(PORTFOLIO)}).status_code == 200
    assert c.get("/api/portfolio/summary").status_code == 200
