"""API tests against Jash's FastAPI backend (POST /api/upload + GET /api/portfolio/*).
Errors are {"detail": "..."}; invalid data 422, non-CSV 415, file > 5 MB 413."""
import pytest

from tests.conftest import DATA, EDGE
from tests.contract import resolve_app

UPLOAD_URL = "/api/upload"
HEALTH_URL = "/health"
PORTFOLIO_FIELD, TRANSACTIONS_FIELD = "portfolio", "transactions"
UPLOAD_ID_KEY = "upload_id"        # ASSUMPTION: confirm key name in the backend README
GET_ROUTES = ["summary", "holdings", "performance", "allocation", "risk", "behavior"]
BAD_REQUEST = (400, 415, 422)

# Files the delivered modules reject (422) vs accept with warnings (200) -- decisions B004-B008.
REJECTED_PORTFOLIOS = ["portfolio_empty", "portfolio_missing_column", "portfolio_invalid_values",
                       "portfolio_negative_quantity", "portfolio_non_numeric_price", "portfolio_zero_buy_price"]
ACCEPTED_PORTFOLIOS = ["portfolio_duplicates", "portfolio_zero_quantity", "portfolio_zero_current_price",
                       "portfolio_single_holding", "portfolio_concentrated", "portfolio_all_losses"]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    return TestClient(resolve_app())


def upload(client, portfolio, transactions=None, filename=None, content=None, ctype="text/csv"):
    body = content if content is not None else portfolio.read_bytes()
    files = {PORTFOLIO_FIELD: (filename or portfolio.name, body, ctype)}
    if transactions:
        files[TRANSACTIONS_FIELD] = (transactions.name, transactions.read_bytes(), "text/csv")
    return client.post(UPLOAD_URL, files=files)


@pytest.fixture(scope="module")
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


@pytest.mark.xfail(reason="EXPECTED: Health Score module not yet added to the backend (owner: Jash, section 9)")
def test_upload_includes_health_score(uploaded):
    score = uploaded.get("health_score")
    score = score.get("score") if isinstance(score, dict) else score
    assert score is not None and 0 <= score <= 100


@pytest.mark.parametrize("route", GET_ROUTES)
def test_get_routes_return_json_after_upload(client, uploaded, route):
    assert UPLOAD_ID_KEY in uploaded, f"upload response has no {UPLOAD_ID_KEY!r}; fix UPLOAD_ID_KEY"
    r = client.get(f"/api/portfolio/{route}", params={"upload_id": uploaded[UPLOAD_ID_KEY]})
    assert r.status_code == 200, r.text
    assert r.json()


@pytest.mark.parametrize("route", GET_ROUTES)
def test_unknown_upload_id_is_404(client, route):
    r = client.get(f"/api/portfolio/{route}", params={"upload_id": "does-not-exist"})
    assert r.status_code == 404 and "detail" in r.json()


def test_same_input_same_output(client):
    ids = [upload(client, DATA / "sample_portfolio.csv", DATA / "sample_transactions.csv").json()[UPLOAD_ID_KEY]
           for _ in range(2)]
    a, b = (client.get("/api/portfolio/summary", params={"upload_id": i}).json() for i in ids)
    assert a == b


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
    # ASSUMPTION (B008): backend passes Prisha's "report, don't reject" behaviour through as 200
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
