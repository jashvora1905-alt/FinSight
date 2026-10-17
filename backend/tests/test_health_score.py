"""Health Score health-v1: formula, bands, failure modes, DataFrame entry point and API wiring."""
import io
import math

import pandas as pd
import pytest

from backend import health_score as hs

from .conftest import PORTFOLIO, make_transactions


def risk(score):
    return {"risk_score": {"score": score}}


def beh(value, status="available"):
    return {"behavior_score": {"status": status, "value": value}}


def available_transactions(portfolio_id="P001"):
    """6 buys then 4 later sells over 60+ days: satisfies the behaviour module's minimum-data rules."""
    rows = ["transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price"]
    syms = ["TCS", "INFY", "ITC", "HDFCBANK", "RELIANCE", "LT"]
    for i, s in enumerate(syms):
        rows.append(f"B{i},{portfolio_id},2026-01-{1 + i * 6:02d},{s},BUY,10,100")
    for i, s in enumerate(syms[:4]):
        rows.append(f"S{i},{portfolio_id},2026-03-{2 + i * 5:02d},{s},SELL,5,120")
    return "\n".join(rows) + "\n"


# ---------- formula ----------

def test_full_score_matches_validated_examples():
    # risk_score 33.75 -> R 66.25 (the diversified sample portfolio from the validation run)
    assert hs.compute_health_score(risk(33.75), beh(81.25))["score"] == pytest.approx(70.75, abs=0.01)
    assert hs.compute_health_score(risk(33.75), beh(50))["score"] == pytest.approx(61.38, abs=0.01)
    assert hs.compute_health_score(risk(33.75), beh(100))["score"] == pytest.approx(76.38, abs=0.01)


def test_full_score_structure():
    r = hs.compute_health_score(risk(33.75), beh(81.25))
    assert r["score_basis"] == "full" and r["coverage"] == 1.0
    assert r["methodology_version"] == "health-v1"
    c = r["components"]
    assert c["risk_diversification"] == {"value": 66.25, "weight_applied": 0.7, "available": True,
                                         "status": None, "source": c["risk_diversification"]["source"]}
    assert c["behavior"]["value"] == 81.25 and c["behavior"]["weight_applied"] == 0.3
    assert c["behavior"]["available"] is True and c["behavior"]["status"] == "available"


@pytest.mark.parametrize("behavior", [None, beh(None, "insufficient_data"), beh(None, "unavailable")])
def test_missing_behaviour_is_explicit_risk_only_not_a_silent_value(behavior):
    r = hs.compute_health_score(risk(33.75), behavior)
    assert r["score"] == 66.25                       # equals R exactly: no 0 / 50 / 100 substituted
    assert r["score_basis"] == "risk_only" and r["coverage"] == 0.7
    b = r["components"]["behavior"]
    assert b["available"] is False and b["value"] is None and b["weight_applied"] == 0.0
    assert r["components"]["risk_diversification"]["weight_applied"] == 1.0
    assert b["status"] == ("not_provided" if behavior is None else behavior["behavior_score"]["status"])


def test_unavailable_status_ignores_a_stray_value():
    assert hs.compute_health_score(risk(20), beh(5, "insufficient_data"))["score"] == 80.0


def test_extremes_hit_0_and_100():
    assert hs.compute_health_score(risk(0), beh(100))["score"] == 100.0
    assert hs.compute_health_score(risk(100), beh(0))["score"] == 0.0


def test_single_holding_cannot_exceed_32_even_with_perfect_behaviour():
    # risk component of a single holding is ~2 -> 0.7*2 + 0.3*100 = 31.4 (documented limitation)
    assert hs.compute_health_score(risk(98), beh(100))["score"] < 32


def test_monotonic_in_both_components():
    scores = [hs.compute_health_score(risk(40), beh(b))["score"] for b in range(0, 101, 10)]
    assert scores == sorted(scores)
    scores = [hs.compute_health_score(risk(r), beh(70))["score"] for r in range(100, -1, -10)]
    assert scores == sorted(scores)


def test_deterministic_and_inputs_not_mutated():
    r, b = risk(33.75), beh(81.25)
    snapshot = (dict(r["risk_score"]), dict(b["behavior_score"]))
    assert hs.compute_health_score(r, b) == hs.compute_health_score(r, b)
    assert (r["risk_score"], b["behavior_score"]) == snapshot


# ---------- bands ----------

@pytest.mark.parametrize("score,band", [
    (100, "Strong"), (75, "Strong"), (74.99, "Moderate"), (50, "Moderate"), (49.99, "Weak"),
    (25, "Weak"), (24.99, "Poor"), (0, "Poor")])
def test_band_edges(score, band):
    assert hs.band_for(score) == band


def test_bands_agree_with_risk_engine_levels():
    """risk level Low is risk_score <= 25, i.e. R >= 75, i.e. band Strong (and so on)."""
    for risk_score, expected in [(25, "Strong"), (25.01, "Moderate"), (50, "Moderate"), (50.01, "Weak"),
                                 (75, "Weak"), (75.01, "Poor")]:
        assert hs.compute_health_score(risk(risk_score))["band"] == expected


# ---------- failure modes (never a silent fallback) ----------

@pytest.mark.parametrize("bad_risk", [{}, {"risk_score": {}}, {"risk_score": None}, None,
                                      risk(-1), risk(101), risk(float("nan")), risk(float("inf")), risk("12"), risk(True)])
def test_invalid_risk_output_raises(bad_risk):
    with pytest.raises(ValueError):
        hs.compute_health_score(bad_risk, None)


@pytest.mark.parametrize("bad_behavior", [{}, {"behavior_score": None}, beh(120), beh(-3), beh(float("nan")), beh("x"), beh(None)])
def test_invalid_behaviour_output_raises(bad_behavior):
    with pytest.raises(ValueError):
        hs.compute_health_score(risk(30), bad_behavior)


def test_score_always_finite_and_in_range():
    for rs in (0, 0.01, 33.33, 99.99, 100):
        for b in (None, 0, 0.01, 99.99, 100):
            s = hs.compute_health_score(risk(rs), None if b is None else beh(b))["score"]
            assert math.isfinite(s) and 0 <= s <= 100


# ---------- DataFrame entry point (signature expected by the test contract) ----------

def frame(text):
    return pd.read_csv(io.StringIO(text))


CONCENTRATED = """portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price
P001,AAA,A Ltd,Equity,IT,100,100,100
P001,BBB,B Ltd,Equity,IT,1,100,100
"""
SINGLE = "portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price\nP001,AAA,A Ltd,Equity,IT,10,100,100\n"
DIVERSIFIED = "portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price\n" + "\n".join(
    f"P001,S{i},Co {i},Equity,{sec},10,100,100" for i, sec in enumerate(
        ["IT", "Banking", "Energy", "Pharma", "FMCG", "Auto", "Metals", "Telecom", "Infra", "Cement", "Retail", "Power"])) + "\n"


def test_dataframe_entry_point_returns_score_key():
    r = hs.calculate_health_score(frame(PORTFOLIO))
    assert 0 <= r["score"] <= 100 and r["score_basis"] == "risk_only"


def test_entry_point_orders_portfolios_sensibly():
    d, c, s = (hs.calculate_health_score(frame(t))["score"] for t in (DIVERSIFIED, CONCENTRATED, SINGLE))
    assert d > c > s


def test_entry_point_with_transactions_is_full_score():
    r = hs.calculate_health_score(frame(PORTFOLIO), frame(available_transactions()))
    assert r["score_basis"] == "full" and r["components"]["behavior"]["available"] is True


def test_entry_point_too_few_transactions_is_risk_only():
    r = hs.calculate_health_score(frame(PORTFOLIO), frame(make_transactions(n=3)))
    assert r["score_basis"] == "risk_only"


def test_entry_point_empty_transactions_frame_is_treated_as_not_provided():
    empty = frame(make_transactions()).iloc[0:0]
    assert hs.calculate_health_score(frame(PORTFOLIO), empty)["score_basis"] == "risk_only"


def test_entry_point_poor_behaviour_scores_below_good_behaviour_on_same_portfolio():
    good = frame(available_transactions())
    poor_rows = ["transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price"]
    start = pd.Timestamp("2026-01-01")
    for k in range(8):  # buy, then sell 2 days later at -8%: every matched sale is a short-hold loss; spans > 30 days
        buy, sell = start + pd.Timedelta(days=k * 5), start + pd.Timedelta(days=k * 5 + 2)
        poor_rows.append(f"PB{k},P001,{buy.date()},TCS,BUY,10,100")
        poor_rows.append(f"PS{k},P001,{sell.date()},TCS,SELL,10,92")
    poor = frame("\n".join(poor_rows) + "\n")
    s_good = hs.calculate_health_score(frame(PORTFOLIO), good)
    s_poor = hs.calculate_health_score(frame(PORTFOLIO), poor)
    assert s_poor["components"]["behavior"]["available"] and s_poor["score"] < s_good["score"]


@pytest.mark.parametrize("bad", [
    pd.DataFrame(),
    frame("portfolio_id,symbol\nP001,TCS\n"),
    frame(PORTFOLIO.replace(",10,2400,", ",-10,2400,")),
])
def test_entry_point_invalid_portfolio_raises_value_error(bad):
    with pytest.raises(ValueError):
        hs.calculate_health_score(bad)


def test_entry_point_unknown_portfolio_id_raises_value_error():
    with pytest.raises(ValueError):
        hs.calculate_health_score(frame(PORTFOLIO), portfolio_id="NOPE")


# ---------- API wiring ----------

def test_upload_returns_risk_only_health_score_without_transactions(post):
    body = post().json()
    h = body["health_score"]
    assert h["score_basis"] == "risk_only" and h["coverage"] == 0.7 and h["methodology_version"] == "health-v1"
    assert h["score"] == pytest.approx(100 - body["risk"]["risk_score"]["score"], abs=0.01)
    assert h["band"] == hs.band_for(h["score"])


def test_upload_with_sufficient_transactions_returns_full_score_matching_formula(post):
    body = post(transactions=available_transactions()).json()
    h, b = body["health_score"], body["behavior"]["behavior_score"]
    assert b["status"] == "available"
    expected = 0.7 * (100 - body["risk"]["risk_score"]["score"]) + 0.3 * b["value"]
    assert h["score_basis"] == "full" and h["score"] == pytest.approx(expected, abs=0.01)


def test_upload_with_too_little_transaction_history_is_risk_only(post):
    body = post(transactions=make_transactions(n=3)).json()
    assert body["behavior"]["behavior_score"]["status"] != "available"
    assert body["health_score"]["score_basis"] == "risk_only"


def test_health_score_endpoint(client, post):
    assert client.get("/api/portfolio/health-score").status_code == 404
    up = post(transactions=available_transactions()).json()
    r = client.get("/api/portfolio/health-score")
    assert r.status_code == 200 and r.json() == up["health_score"]
    assert client.get("/api/portfolio/health-score", params={"upload_id": "nope"}).status_code == 404


def test_same_input_same_health_score(post):
    assert post(transactions=available_transactions()).json() == post(transactions=available_transactions()).json()


def test_invalid_upload_has_no_health_score_and_is_422(post):
    r = post(portfolio="portfolio_id,symbol\nP001,TCS\n")
    assert r.status_code == 422 and "health_score" not in r.json()


def test_rounding_is_exact_half_up_not_binary_float():
    """0.7 * 6 + 0.3 * 81.25 = 28.575 exactly -> 28.58 (plain float arithmetic would give 28.57)."""
    assert hs.compute_health_score(risk(94), beh(81.25))["score"] == 28.58
    assert hs.compute_health_score(risk(98), beh(81.25))["score"] == 25.78
