import pytest

from .conftest import PORTFOLIO, PRICE_HISTORY, TWO_PORTFOLIOS, csv_file, make_transactions


# ---------- health & happy path ----------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_upload_portfolio_only_matches_documented_worked_example(post):
    r = post()
    assert r.status_code == 200, r.text
    body = r.json()
    s = body["analytics"]["summary"]
    # analytics_methodology.md §6 worked example
    assert (s["invested_value"], s["current_value"], s["pnl"], s["return_pct"]) == (53500.0, 60200.0, 6700.0, 12.52)
    assert body["portfolio_id"] == "P001"
    assert body["behavior"] is None
    assert body["inputs"] == {"transactions_provided": False, "price_history_provided": False}
    assert 0 <= body["risk"]["risk_score"]["score"] <= 100
    assert body["risk"]["risk_metrics"]["historical_data_available"] is False
    sectors = {x["name"]: x["weight_pct"] for x in body["analytics"]["allocation"]["by_sector"]}
    assert sectors == {"IT": 55.98, "Energy": 44.02}


def test_upload_with_transactions_includes_behavior(post):
    r = post(transactions=make_transactions())
    assert r.status_code == 200, r.text
    b = r.json()["behavior"]
    assert b["methodology_version"] == "behavior-v1"
    assert b["summary"]["total_trades"] == 12
    assert b["behavior_score"]["status"] in {"available", "insufficient_data"}


def test_upload_with_price_history_enables_historical_risk(post):
    r = post(price_history=PRICE_HISTORY)
    assert r.status_code == 200, r.text
    rm = r.json()["risk"]["risk_metrics"]
    assert rm["historical_data_available"] is True and rm["annualized_volatility_pct"] is not None


def test_same_input_same_output(post):
    assert post(transactions=make_transactions()).json() == post(transactions=make_transactions()).json()


def test_different_input_different_upload_id(post):
    assert post().json()["upload_id"] != post(TWO_PORTFOLIOS).json()["upload_id"]


# ---------- GET endpoints ----------

def test_get_endpoints_before_any_upload_are_404(client):
    for path in ("summary", "holdings", "performance", "allocation", "risk", "behavior"):
        r = client.get(f"/api/portfolio/{path}")
        assert r.status_code == 404 and "upload" in r.json()["detail"].lower(), path


def test_get_endpoints_after_upload(client, post):
    up = post(transactions=make_transactions()).json()
    assert client.get("/api/portfolio/summary").json() == up["analytics"]["summary"]
    assert client.get("/api/portfolio/holdings").json() == up["analytics"]["holdings"]
    assert client.get("/api/portfolio/allocation").json() == up["analytics"]["allocation"]
    assert client.get("/api/portfolio/risk").json() == up["risk"]
    assert client.get("/api/portfolio/behavior").json() == up["behavior"]
    perf = client.get("/api/portfolio/performance").json()
    assert perf["summary"] == up["analytics"]["summary"]
    assert {h["symbol"] for h in perf["holdings"]} == {"RELIANCE", "TCS", "INFY"}
    assert round(sum(h["contribution_pct"] for h in perf["holdings"]), 1) == 12.5


def test_upload_id_selects_specific_upload_and_latest_is_default(client, post):
    first = post().json()
    second = post(TWO_PORTFOLIOS, portfolio_id="P002").json()
    assert client.get("/api/portfolio/summary").json()["number_of_holdings"] == 1  # latest = P002
    r = client.get("/api/portfolio/summary", params={"upload_id": first["upload_id"]})
    assert r.json()["number_of_holdings"] == 3
    assert second["portfolio_id"] == "P002"


def test_reuploading_old_content_makes_it_latest_again(client, post):
    post()
    post(TWO_PORTFOLIOS, portfolio_id="P002")
    post()
    assert client.get("/api/portfolio/summary").json()["number_of_holdings"] == 3


def test_unknown_upload_id_is_404(client):
    assert client.get("/api/portfolio/summary", params={"upload_id": "nope"}).status_code == 404


def test_behavior_get_without_transactions_is_404(client, post):
    post()
    r = client.get("/api/portfolio/behavior")
    assert r.status_code == 404 and "transactions" in r.json()["detail"].lower()


# ---------- portfolio_id / observation window pass-through ----------

def test_portfolio_id_filters_analysis(post):
    r = post(TWO_PORTFOLIOS, portfolio_id="P002")
    assert r.status_code == 200
    assert r.json()["analytics"]["summary"]["number_of_holdings"] == 1


def test_unknown_portfolio_id_is_422(post):
    r = post(portfolio_id="NOPE")
    assert r.status_code == 422 and "NOPE" in r.json()["detail"]


def test_multiple_portfolios_in_transactions_need_portfolio_id(post):
    tx = make_transactions("P001") + make_transactions("P002").split("\n", 1)[1]
    r = post(transactions=tx)
    assert r.status_code == 422 and "portfolio_id" in r.json()["detail"]
    assert post(transactions=tx, portfolio_id="P001").status_code == 200


def test_observation_window_is_passed_to_behavior(post):
    r = post(transactions=make_transactions(), observation_start="2026-01-01", observation_end="2026-03-01")
    assert r.status_code == 200
    freq = r.json()["behavior"]["frequency"]
    assert (freq["observation_start"], freq["observation_end"]) == ("2026-01-01", "2026-03-01")


def test_bad_observation_date_is_422(post):
    r = post(transactions=make_transactions(), observation_end="01/03/2026")
    assert r.status_code == 422


# ---------- invalid input is rejected cleanly (never a 500) ----------

def _bad(post, **kw):
    r = post(**kw)
    assert r.status_code in (400, 413, 415, 422), (r.status_code, r.text)
    assert isinstance(r.json()["detail"], str) and r.json()["detail"]
    return r


def test_missing_portfolio_file(post):
    assert post(portfolio=None).status_code == 422


def test_empty_file(post):
    assert "empty" in _bad(post, portfolio="").json()["detail"].lower()


def test_header_only_file(post):
    _bad(post, portfolio=PORTFOLIO.splitlines()[0] + "\n")


def test_missing_required_column(post):
    r = _bad(post, portfolio="portfolio_id,symbol,quantity\nP001,TCS,5\n")
    assert "Missing required columns" in r.json()["detail"]


def test_non_numeric_and_negative_values(post):
    _bad(post, portfolio=PORTFOLIO.replace(",10,2400,", ",abc,2400,"))
    _bad(post, portfolio=PORTFOLIO.replace(",10,2400,", ",-10,2400,"))


def test_non_csv_extension_is_415(client):
    r = client.post("/api/upload", files={"portfolio": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_non_utf8_file(client):
    r = client.post("/api/upload", files={"portfolio": ("p.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert r.status_code == 422 and "UTF-8" in r.json()["detail"]


def test_too_large_file(client, monkeypatch):
    from backend import routes
    monkeypatch.setattr(routes, "MAX_UPLOAD_BYTES", 50)
    r = client.post("/api/upload", files={"portfolio": csv_file(PORTFOLIO)})
    assert r.status_code == 413


def test_transactions_missing_columns(post):
    r = _bad(post, transactions="transaction_id,date,ticker,type,quantity,price,fees\nT1,2024-01-10,TCS,BUY,1,1,0\n")
    assert "missing columns" in r.json()["detail"].lower()


@pytest.mark.parametrize("mutate", [
    lambda t: t.replace("BUY", "HOLD", 1),
    lambda t: t.replace("2026-01-01", "not-a-date", 1),
    lambda t: t.replace(",100\n", ",-5\n", 1),
])
def test_invalid_transaction_rows(post, mutate):
    _bad(post, transactions=mutate(make_transactions()))


def test_unusable_price_history_is_reported_by_risk_engine_not_rejected(post):
    """risk_engine's documented behaviour: unusable history -> historical_data_available=False + reason."""
    r = post(price_history="when,what\n1,2\n")
    assert r.status_code == 200
    rm = r.json()["risk"]["risk_metrics"]
    assert rm["historical_data_available"] is False and "price columns" in rm["reason"]


def test_bad_upload_is_not_stored(client, post):
    post(portfolio="portfolio_id,symbol\nP001,TCS\n")
    assert client.get("/api/portfolio/summary").status_code == 404


def test_wrong_method(client):
    assert client.get("/api/upload").status_code == 405
    assert client.post("/health").status_code == 405


def test_unexpected_error_returns_clean_500(client, post, monkeypatch):
    from backend import service
    monkeypatch.setattr(service, "analyze_portfolio", lambda *a, **k: 1 / 0)
    r = post()
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error."}


def test_cors_header_for_vite_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
