"""Health Score health-v2 (README dimensions: Performance, Risk, Diversification, Behaviour)."""
import io
import math
from decimal import Decimal

import pandas as pd
import pytest

from backend.services import health_score as hs

from tests.backend_support import (CONCENTRATED, DIVERSIFIED, PORTFOLIO, SINGLE, available_transactions,  # noqa: F401
                              client, make_transactions, poor_transactions, post)


def analytics(ret=11.6, price_missing=0):
    return {"summary": {"return_pct": ret}, "holdings": [{"price_missing": i < price_missing} for i in range(3)]}


def risk(components=None, weights=None, div=60.0, history=False, gaps=()):
    components = components or {"holding_concentration": 50.0, "sector_concentration": 20.0, "diversification_risk": 40.0}
    weights = weights or {"holding_concentration": 0.40, "sector_concentration": 0.35, "diversification_risk": 0.25}
    return {"risk_score": {"score": 0.0, "components": components, "component_weights": weights},
            "diversification": {"diversification_score": div, "diversification_gaps": list(gaps)},
            "risk_metrics": {"historical_data_available": history}}


def beh(value, status="available", reasons=()):
    return {"behavior_score": {"status": status, "value": value, "reasons": list(reasons)}}


# ---------- formula (hand-computed) ----------

def test_full_score_hand_computed():
    # risk_ex = (0.40*50 + 0.35*20)/0.75 = 36 -> R = 64; P = 50 + 50*11.6/30 = 69.3333; D = 60; B = 80
    # score = 0.35*64 + 0.25*60 + 0.25*80 + 0.15*69.3333 = 22.4 + 15 + 20 + 10.4 = 67.8
    r = hs.compute_health_score(analytics(), risk(), beh(80))
    assert r["score"] == 67.8 and r["band"] == "Moderate"
    assert r["score_basis"] == "full" and r["coverage"] == 1.0 and r["missing_components"] == []
    c = r["components"]
    assert (c["risk"]["value"], c["diversification"]["value"], c["behavior"]["value"], c["performance"]["value"]) == (64.0, 60.0, 80.0, 69.33)
    assert (c["risk"]["weight_applied"], c["diversification"]["weight_applied"],
            c["behavior"]["weight_applied"], c["performance"]["weight_applied"]) == (0.35, 0.25, 0.25, 0.15)
    assert r["methodology_version"] == "health-v2"


def test_risk_component_excludes_diversification_risk_so_it_is_not_counted_twice():
    low_div = hs.compute_health_score(analytics(), risk(components={"holding_concentration": 50.0, "sector_concentration": 20.0, "diversification_risk": 0.0}), beh(80))
    high_div = hs.compute_health_score(analytics(), risk(components={"holding_concentration": 50.0, "sector_concentration": 20.0, "diversification_risk": 100.0}), beh(80))
    assert low_div["components"]["risk"]["value"] == high_div["components"]["risk"]["value"] == 64.0


def test_risk_component_with_price_history_components():
    comps = {"holding_concentration": 50.0, "sector_concentration": 20.0, "diversification_risk": 40.0, "volatility": 30.0, "drawdown": 10.0}
    w = {"holding_concentration": 0.25, "sector_concentration": 0.20, "diversification_risk": 0.15, "volatility": 0.25, "drawdown": 0.15}
    # (12.5 + 4 + 7.5 + 1.5) / 0.85 = 30 -> R = 70
    assert hs.compute_health_score(analytics(), risk(comps, w, history=True), None)["components"]["risk"]["value"] == 70.0


@pytest.mark.parametrize("ret,expected", [(0, 50.0), (30, 100.0), (-30, 0.0), (15, 75.0), (-15, 25.0), (60, 100.0), (-100, 0.0), (11.6, 69.33)])
def test_performance_mapping(ret, expected):
    assert hs.compute_health_score(analytics(ret), risk(), None)["components"]["performance"]["value"] == expected


def test_score_equals_100_minus_points_lost():
    r = hs.compute_health_score(analytics(), risk(), beh(80))
    lost = sum(c["points_lost"] for c in r["components"].values())
    assert r["score"] == pytest.approx(100 - lost, abs=0.02)
    assert sum(c["contribution_points"] for c in r["components"].values()) == pytest.approx(r["score"], abs=0.02)


def test_applied_weights_always_sum_to_one():
    for beh_arg, ret in [(beh(80), 5), (None, 5), (beh(80), None), (None, None)]:
        r = hs.compute_health_score(analytics(ret), risk(), beh_arg)
        assert sum(c["weight_applied"] for c in r["components"].values()) == pytest.approx(1.0, abs=0.02)  # shown rounded to 2 dp


# ---------- missing components: explicit reweighting, never a made-up value ----------

def test_missing_behaviour_is_partial_and_rescaled():
    # weights 0.35, 0.25, 0.15 rescaled by 0.75 -> 63.7333
    r = hs.compute_health_score(analytics(), risk(), None)
    assert r["score"] == 63.73 and r["score_basis"] == "partial" and r["coverage"] == 0.75
    assert r["missing_components"] == ["behavior"]
    b = r["components"]["behavior"]
    assert (b["available"], b["value"], b["weight_applied"], b["status"]) == (False, None, 0.0, "not_provided")
    assert any("Provisional" in n for n in r["explanation"]["notes"]) and r["explanation"]["summary"].endswith("Provisional.")


@pytest.mark.parametrize("status", ["insufficient_data", "unavailable"])
def test_unavailable_behaviour_status_is_reported_and_stray_value_ignored(status):
    r = hs.compute_health_score(analytics(), risk(), beh(5, status, ["At least 10 transactions are required."]))
    assert r["components"]["behavior"]["status"] == status and r["components"]["behavior"]["value"] is None
    assert r["score"] == 63.73
    assert "Behaviour: At least 10 transactions are required." in r["explanation"]["notes"]


def test_missing_performance_and_both_missing():
    r = hs.compute_health_score(analytics(None), risk(), beh(80))
    assert r["missing_components"] == ["performance"] and r["coverage"] == 0.85 and r["score_basis"] == "partial"
    r = hs.compute_health_score(analytics(None), risk(), None)
    assert r["missing_components"] == ["performance", "behavior"] and r["coverage"] == 0.6
    assert r["components"]["risk"]["weight_applied"] == pytest.approx(0.35 / 0.6, abs=0.01)


# ---------- explanation ----------

def test_drivers_sorted_by_points_lost_and_summary():
    r = hs.compute_health_score(analytics(), risk(), beh(80))
    lost = [d["points_lost"] for d in r["explanation"]["drivers"]]
    assert lost == sorted(lost, reverse=True)
    assert r["explanation"]["drivers"][0]["component"] == "risk"
    assert r["explanation"]["summary"].startswith("Health score 67.80 (Moderate). Largest drag: Risk")


def test_notes_pass_through_module_gaps_and_data_quality():
    r = hs.compute_health_score(analytics(price_missing=2), risk(gaps=["A single holding exceeds 35% of current portfolio value."]), beh(80))
    notes = r["explanation"]["notes"]
    assert "Diversification: A single holding exceeds 35% of current portfolio value." in notes
    assert any("no historical price data" in n for n in notes)
    assert any("2 holding(s) with no current price" in n for n in notes)
    assert not any("no historical price data" in n for n in hs.compute_health_score(analytics(), risk(history=True), beh(80))["explanation"]["notes"])


def test_perfect_components_have_no_drag_text():
    r = hs.compute_health_score(analytics(30), risk(components={"holding_concentration": 0.0, "sector_concentration": 0.0, "diversification_risk": 0.0}, div=100.0), beh(100))
    assert r["score"] == 100.0 and r["band"] == "Strong" and "Largest drag" not in r["explanation"]["summary"]


# ---------- bands / rounding / properties ----------

@pytest.mark.parametrize("score,band", [(100, "Strong"), (75, "Strong"), (74.99, "Moderate"), (50, "Moderate"),
                                        (49.99, "Weak"), (25, "Weak"), (24.99, "Poor"), (0, "Poor")])
def test_band_edges(score, band):
    assert hs.band_for(score) == band


def test_rounding_is_exact_half_up():
    assert hs._round2(Decimal("28.575")) == 28.58 and hs._round2(Decimal("25.775")) == 25.78 and hs._round2(Decimal("0.004")) == 0.0


def test_monotonic_in_every_component():
    base = lambda **kw: hs.compute_health_score(analytics(kw.get("ret", 11.6)), risk(div=kw.get("div", 60.0)), beh(kw.get("b", 80)))["score"]
    for key, values in {"b": range(0, 101, 10), "div": range(0, 101, 10), "ret": range(-40, 41, 10)}.items():
        scores = [base(**{key: v}) for v in values]
        assert scores == sorted(scores), key


def test_deterministic_and_inputs_not_mutated():
    a, r, b = analytics(), risk(), beh(80)
    import copy
    snap = copy.deepcopy((a, r, b))
    assert hs.compute_health_score(a, r, b) == hs.compute_health_score(a, r, b)
    assert (a, r, b) == snap


def test_score_always_finite_and_in_range():
    for ret in (None, -100, -30, 0, 30, 500):
        for bv in (None, 0, 100):
            s = hs.compute_health_score(analytics(ret), risk(), None if bv is None else beh(bv))["score"]
            assert math.isfinite(s) and 0 <= s <= 100


# ---------- failure modes: bad module output is an error, never a silent default ----------

@pytest.mark.parametrize("bad", [{}, {"summary": None}, {"summary": {}}, {"summary": {"return_pct": float("nan")}},
                                 {"summary": {"return_pct": "9"}}, {"summary": {"return_pct": True}}, None])
def test_invalid_analytics_raises(bad):
    with pytest.raises(ValueError):
        hs.compute_health_score(bad, risk(), None)


@pytest.mark.parametrize("bad", [{}, {"risk_score": {}}, {"risk_score": {"components": {}, "component_weights": {}}},
                                 {"risk_score": {"components": {"holding_concentration": 120.0}, "component_weights": {"holding_concentration": 1.0}},
                                  "diversification": {"diversification_score": 50}},
                                 {**risk(), "diversification": {"diversification_score": 101}},
                                 {**risk(), "diversification": {}}, None])
def test_invalid_risk_raises(bad):
    with pytest.raises(ValueError):
        hs.compute_health_score(analytics(), bad, None)


@pytest.mark.parametrize("bad", [{}, {"behavior_score": None}, beh(120), beh(-3), beh(float("nan")), beh("x"), beh(None)])
def test_invalid_behaviour_raises(bad):
    with pytest.raises(ValueError):
        hs.compute_health_score(analytics(), risk(), bad)


# ---------- DataFrame entry point (signature the test contract expects) ----------

def frame(text):
    return pd.read_csv(io.StringIO(text))


def test_entry_point_returns_score_key_and_partial_without_transactions():
    r = hs.calculate_health_score(frame(PORTFOLIO))
    assert 0 <= r["score"] <= 100 and r["score_basis"] == "partial"


def test_entry_point_orders_portfolios_sensibly():
    d, c, s = (hs.calculate_health_score(frame(t))["score"] for t in (DIVERSIFIED, CONCENTRATED, SINGLE))
    assert d > c > s


def test_entry_point_full_score_with_sufficient_transactions():
    r = hs.calculate_health_score(frame(PORTFOLIO), frame(available_transactions()))
    assert r["score_basis"] == "full" and r["components"]["behavior"]["available"]


def test_entry_point_too_few_or_empty_transactions_is_partial():
    assert hs.calculate_health_score(frame(PORTFOLIO), frame(make_transactions(n=3)))["score_basis"] == "partial"
    assert hs.calculate_health_score(frame(PORTFOLIO), frame(make_transactions()).iloc[0:0])["score_basis"] == "partial"


def test_entry_point_poor_behaviour_scores_below_good_behaviour_on_same_portfolio():
    good = hs.calculate_health_score(frame(PORTFOLIO), frame(available_transactions()))
    poor = hs.calculate_health_score(frame(PORTFOLIO), frame(poor_transactions()))
    assert poor["components"]["behavior"]["available"] and poor["score"] < good["score"]


@pytest.mark.parametrize("bad", [pd.DataFrame(), frame("portfolio_id,symbol\nP001,TCS\n"), frame(PORTFOLIO.replace(",10,2400,", ",-10,2400,"))])
def test_entry_point_invalid_portfolio_raises_value_error(bad):
    with pytest.raises(ValueError):
        hs.calculate_health_score(bad)


def test_entry_point_unknown_portfolio_id_raises_value_error():
    with pytest.raises(ValueError):
        hs.calculate_health_score(frame(PORTFOLIO), portfolio_id="NOPE")


# ---------- API wiring ----------

def test_health_endpoint_matches_upload_and_has_readme_dimensions(client, post):
    up = post(transactions=available_transactions()).json()
    h = client.get("/api/portfolio/health")
    assert h.status_code == 200 and h.json() == up["health_score"]
    assert set(h.json()["components"]) == {"performance", "risk", "diversification", "behavior"}
    assert h.json()["score_basis"] == "full" and h.json()["explanation"]["drivers"]


def test_upload_without_transactions_returns_partial_health(post):
    h = post().json()["health_score"]
    assert h["score_basis"] == "partial" and h["coverage"] == 0.75 and h["missing_components"] == ["behavior"]


def test_upload_health_matches_formula_on_module_outputs(post):
    body = post(transactions=available_transactions()).json()
    c = body["health_score"]["components"]
    assert c["diversification"]["value"] == body["risk"]["diversification"]["diversification_score"]
    assert c["behavior"]["value"] == body["behavior"]["behavior_score"]["value"]
    assert c["performance"]["value"] == pytest.approx(min(100, max(0, 50 + 50 * body["analytics"]["summary"]["return_pct"] / 30)), abs=0.01)
