"""API tests against Jash's FastAPI backend (README "API Structure").
POST /api/portfolio/upload; GET /api/portfolio/summary|holdings|performance|allocation|risk|
diversification|behavior|health|insights. Optional ?portfolio_id= (default: latest upload).
Errors are {"detail": "..."}; invalid data 422, non-CSV 415, file > 5 MB 413, insights 501 until the AI module lands.
"""
import pytest

from tests.conftest import DATA, EDGE
from tests.contract import resolve_app

UPLOAD_URL = "/api/portfolio/upload"
HEALTH_URL = "/health"                      # service liveness only
PORTFOLIO_FIELD, TRANSACTIONS_FIELD = "portfolio", "transactions"
GET_ROUTES = ["summary", "holdings", "performance", "allocation", "risk",
              "diversification", "behavior", "health"]
BAD_REQUEST = (400, 415, 422)

# Files the delivered modules reject (422) vs accept with warnings (200) -- decisions B004-B008.
REJECTED_PORTFOLIOS = ["portfolio_empty", "portfolio_missing_column", "portfolio_invalid_values",
                       "portfolio_negative_quantity", "portfolio_non_numeric_price",
                       "portfolio_zero_buy_price", "portfolio_blank_symbol"]
ACCEPTED_PORTFOLIOS = ["portfolio_duplicates", "portfolio_zero_quantity", "portfolio_zero_current_price",
                       "portfolio_single_holding", "portfolio_concentrated", "portfolio_all_losses"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from fastapi.testclient import TestClient
    from backend import config
    config.DB_PATH = tmp_path_factory.mktemp("db") / "test.db"     # never touch backend/finsight.db
    return TestClient(resolve_app())


def upload(client, portfolio, transactions=None, filename=None, content=None,
           ctype="text/csv", form=None):
    body = content if content is not None else portfolio.read_bytes()
    files = {PORTFOLIO_FIELD: (filename or portfolio.name, body, ctype)}
    if transactions:
        files[TRANSACTIONS_FIELD] = (transactions.name, transactions.read_bytes(), "text/csv")
    return client.post(UPLOAD_URL, files=files, data=form or {})


@pytest.fixture   # per-test on purpose: a portfolio-only upload replaces the stored transactions
def uploaded(client):
    r = upload(client, DATA / "sample_portfolio.csv", DATA / "sample_transactions.csv")
    assert r.status_code == 200, r.text
    return r.json()


def test_health_endpoint(client):
    assert client.get(HEALTH_URL).status_code == 200


def test_sample_files_upload_returns_200(uploaded):
    assert isinstance(uploaded, dict) and uploaded


def test_portfolio_only_upload(client):
    assert upload(client, DATA / "sample_portfolio.csv").status_code == 200


def test_upload_includes_health_score(uploaded):
    score = uploaded.get("health_score")
    score = score.get("score") if isinstance(score, dict) else score
    assert score is not None and 0 <= score <= 100


@pytest.mark.parametrize("route", GET_ROUTES)
def test_get_routes_return_json_after_upload(client, uploaded, route):
    r = client.get(f"/api/portfolio/{route}", params={"portfolio_id": uploaded["portfolio_id"]})
    assert r.status_code == 200, r.text
    assert r.json()


@pytest.mark.parametrize("route", GET_ROUTES)
def test_unknown_portfolio_id_is_404(client, route):
    r = client.get(f"/api/portfolio/{route}", params={"portfolio_id": "does-not-exist"})
    assert r.status_code == 404 and "detail" in r.json()


def test_same_input_same_output(client):
    a, b = (upload(client, DATA / "sample_portfolio.csv", DATA / "sample_transactions.csv").json()
            for _ in range(2))
    assert a == b


# ---- behaviour new in the rebuilt backend, at the level of our sample data ----

def test_uploading_twice_replaces_rather_than_duplicates(client):
    first = upload(client, DATA / "sample_portfolio.csv", DATA / "sample_transactions.csv")
    summary_1 = client.get("/api/portfolio/summary", params={"portfolio_id": "P001"}).json()
    upload(client, DATA / "sample_portfolio.csv", DATA / "sample_transactions.csv")
    summary_2 = client.get("/api/portfolio/summary", params={"portfolio_id": "P001"}).json()
    assert first.status_code == 200 and summary_1 == summary_2


def test_summary_get_matches_upload_response(client, uploaded):
    got = client.get("/api/portfolio/summary", params={"portfolio_id": "P001"}).json()
    assert got == uploaded["analytics"]["summary"]


def test_insights_is_501_until_ai_module_is_integrated(client, uploaded):
    assert client.get("/api/portfolio/insights", params={"portfolio_id": "P001"}).status_code == 501


def test_duplicate_transaction_id_is_rejected(client, tmp_path):
    lines = (DATA / "sample_transactions.csv").read_text().splitlines()
    dup = tmp_path / "dup_transactions.csv"
    dup.write_text("\n".join(lines + [lines[1]]) + "\n")
    r = upload(client, DATA / "sample_portfolio.csv", dup)
    assert r.status_code == 422 and "duplicate transaction_id" in r.json()["detail"]


def test_header_only_transactions_count_as_not_provided(client):
    r = upload(client, DATA / "sample_portfolio.csv", EDGE / "transactions_empty.csv")
    assert r.status_code == 200 and r.json()["inputs"]["transactions_provided"] is False


def test_transactions_for_unknown_portfolio_id_are_rejected(client):
    r = upload(client, DATA / "sample_portfolio.csv", EDGE / "transactions_multi_portfolio.csv")
    assert r.status_code == 422 and "detail" in r.json()


def test_multi_portfolio_transactions_accepted_with_portfolio_id(client):
    # portfolio_id is a multipart form field on upload (backend/api/portfolio.py)
    r = upload(client, DATA / "sample_portfolio.csv", EDGE / "transactions_multi_portfolio.csv",
               form={"portfolio_id": "P001"})
    assert r.status_code == 200, r.text


# ---- validation ----

@pytest.mark.parametrize("name", REJECTED_PORTFOLIOS)
def test_invalid_portfolio_is_rejected_with_422(client, name):
    r = upload(client, EDGE / f"{name}.csv")
    assert r.status_code == 422, f"{name}: got {r.status_code}"
    assert "detail" in r.json()


@pytest.mark.parametrize("name", ACCEPTED_PORTFOLIOS)
def test_lenient_portfolios_are_accepted(client, name):
    assert upload(client, EDGE / f"{name}.csv").status_code == 200, name


def test_invalid_transactions_rejected(client):
    r = upload(client, DATA / "sample_portfolio.csv", EDGE / "transactions_invalid.csv")
    assert r.status_code == 422 and "detail" in r.json()


def test_oversell_transactions_accepted_with_warning(client):
    # B008: Prisha's "report, don't reject" behaviour reaches the API as 200
    assert upload(client, DATA / "sample_portfolio.csv", EDGE / "transactions_oversell.csv").status_code == 200


def test_missing_file_rejected(client):
    assert client.post(UPLOAD_URL).status_code in BAD_REQUEST


def test_wrong_method_not_allowed(client):
    assert client.get(UPLOAD_URL).status_code == 405


def test_non_csv_upload_is_415(client):
    r = upload(client, DATA / "sample_portfolio.csv", filename="notes.txt",
               content=b"this is not a portfolio", ctype="text/plain")
    assert r.status_code == 415 and "detail" in r.json()


def test_oversized_upload_is_413(client):
    big = (DATA / "sample_portfolio.csv").read_bytes() + b"#" * (5 * 1024 * 1024 + 1)
    assert upload(client, DATA / "sample_portfolio.csv", content=big).status_code == 413
