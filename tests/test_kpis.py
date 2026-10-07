

"""Tests for the North Star KPI (Phase 3, decisions D1-D7).  Run:  python -m pytest -q

Small hand-built companies give answers you can check on paper; one golden test pins the real data.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.kpis import build, input_validity, like_for_like, north_star, ttm_panel


def make_company(revenue_k, oi_k, symbol="TEST", start="2023-03-31"):
    """Quarterly rows (values in thousands -> whole currency units) whose accounting identities hold."""
    n = len(revenue_k)
    rev = pd.Series(revenue_k, dtype="float64") * 1000
    oi = pd.Series(oi_k, dtype="float64") * 1000
    cost = (rev / 2).round(-3)
    gp = rev - cost
    return pd.DataFrame({
        "symbol": symbol,
        "fiscalDateEnding": pd.date_range(start, periods=n, freq="QE"),
        "totalRevenue": rev, "costOfRevenue": cost, "grossProfit": gp,
        "operatingExpenses": gp - oi,                               # so OI = GP - opex holds exactly
        "operatingIncome": oi,
        "netIncome": pd.Series(range(1, n + 1), dtype="float64") * 1000,  # varies, so no copied quarters
    })


def run_chain(df):
    return north_star(ttm_panel(input_validity(df)))


def test_growth_and_margin_known_answer():
    # Last year: TTM revenue 400k, OI 40k (10%). This year: 500k and 60k (12%).
    df = make_company([100] * 4 + [125] * 4, [10] * 4 + [15] * 4)
    last = run_chain(df).iloc[-1]
    assert last["ttm_oi"] == 60_000 and last["base_ttm_oi"] == 40_000
    assert last["ns_growth"] == pytest.approx(0.50)
    assert last["margin_change_pp"] == pytest.approx(2.0)
    assert last["quality_quadrant"] == "growth with margin up"
    # KPI tree identity: 1 + g_OI = (1 + g_revenue) x (margin_t / margin_base) = 1.25 x 1.2
    g_rev = last["ttm_revenue"] / last["base_ttm_revenue"] - 1
    assert 1 + last["ns_growth"] == pytest.approx((1 + g_rev) * last["ttm_margin"] / last["base_margin"])


def test_missing_quarter_breaks_the_ttm():
    # Drop the 3rd quarter: last year's TTM can no longer be built, so there is no growth.
    df = make_company([100] * 4 + [125] * 4, [10] * 4 + [15] * 4).drop(index=2)
    last = run_chain(df).iloc[-1]
    assert pd.notna(last["ttm_oi"]) and pd.isna(last["base_ttm_oi"])
    assert last["ns_status"] == "no TTM pair" and pd.isna(last["ns_growth"])


def test_repeat_is_stale_only_when_its_identity_breaks():
    df = make_company([100, 110], [10, 10])           # OI repeats, but OI = GP - opex holds
    assert not input_validity(df)["stale_oi"].any()
    df.loc[1, "operatingExpenses"] = 20_000           # identity now off by 25% of revenue
    assert input_validity(df)["stale_oi"].tolist() == [False, True]


@pytest.mark.parametrize("base_oi, oi, expected", [
    (-40, 20, "turned profitable"),
    (-40, -20, "loss narrowed"),
    (-20, -40, "loss widened or flat"),
    (1, 30, "base margin below 2%"),                  # base margin 1/100 = 1%
    (40, 60, "defined"),
])
def test_status_labels_for_awkward_bases(base_oi, oi, expected):
    panel = pd.DataFrame({"symbol": ["TEST"], "ttm_oi": [oi], "ttm_revenue": [100.0],
                          "base_ttm_oi": [base_oi], "base_ttm_revenue": [100.0]})
    row = north_star(panel).iloc[0]
    assert row["ns_status"] == expected
    assert pd.isna(row["ns_growth"]) == (expected != "defined")


def test_like_for_like_is_ratio_of_sums_not_mean_of_growths():
    # A: 100 -> 200 (+100%). B: 900 -> 900 (0%). TSM is non-USD, C has no base: both excluded.
    panel = pd.DataFrame({
        "calendar_quarter": ["2025Q3"] * 4, "symbol": ["A", "B", "TSM", "C"],
        "ttm_oi": [200.0, 900.0, 500.0, 50.0], "base_ttm_oi": [100.0, 900.0, 100.0, None],
        "ttm_revenue": [1000.0, 3000.0, 1000.0, 100.0], "base_ttm_revenue": [1000.0, 3000.0, 1000.0, None],
    })
    row = like_for_like(panel).iloc[0]
    assert row["companies"] == 2
    assert row["ns_growth"] == pytest.approx(0.10)    # (200 + 900) / (100 + 900) - 1; the mean would be 50%


def test_golden_numbers_on_the_real_file():
    valid, ns, lfl = build()
    assert int((~valid["input_valid"]).sum()) == 41
    assert int(valid["stale_oi"].sum()) == 11 and int(valid["is_manual"].sum()) == 7
    assert int(ns["ttm_oi"].notna().sum()) == 1611
    assert int((ns["ns_status"] == "defined").sum()) == 1414
    q3 = lfl[lfl["calendar_quarter"] == pd.Period("2025Q3", "Q")].iloc[0]
    assert q3["companies"] == 20 and q3["ns_growth"] == pytest.approx(0.1673, abs=5e-5)