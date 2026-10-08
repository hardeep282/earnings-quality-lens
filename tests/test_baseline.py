

"""Tests for the seasonal-naive baseline (step S1.1).  Run:  python -m pytest -q

Unit tests use tiny series whose answers are worked out by hand in the comments.
Integration tests build the pipeline into a temporary database, so your working
data/processed/earnings.duckdb is never touched.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.baseline import (
    backtest,
    forecast_next,
    load_series,
    mase_table,
    quarter_key,
    scale_stats,
    seasonal_naive,
)
from src.pipeline import run


def series(values, start=1):
    return pd.Series(values, index=pd.RangeIndex(start, start + len(values)), dtype=float)


def test_quarter_key_matches_gold_dim_quarter():
    # gold.dim_quarter: calendar_year = (key - 1) // 4, quarter = (key - 1) % 4 + 1
    assert quarter_key("2015Q4") == 8064
    assert ((8064 - 1) // 4, (8064 - 1) % 4 + 1) == (2015, 4)


def test_seasonal_naive_repeats_last_observed_year():
    y = series([10, 20, 30, 40, 12, 22, 32, 42])           # keys 1..8
    # h = 1..4 -> keys 5..8 ; h = 5..8 -> k = 1 -> keys 5..8 again
    assert seasonal_naive(y, origin=8).tolist() == [12, 22, 32, 42]
    assert seasonal_naive(y, origin=8, horizon=8).tolist() == [12, 22, 32, 42] * 2


def test_scale_stats_by_hand():
    y = series([10, 20, 30, 40, 13, 21, 30, 44])
    # seasonal differences: 3, 1, 0, 4 -> MAE = 8/4 = 2.0 ; RMS = sqrt(26/4) = 2.5495
    mae, rms, pairs = scale_stats(y, origin=8)
    assert mae == pytest.approx(2.0)
    assert rms == pytest.approx(np.sqrt(6.5))
    assert pairs == 4


def test_scale_never_sees_after_the_origin():
    y = series([10, 20, 30, 40, 13, 21, 30, 44])
    before = scale_stats(y, origin=6)
    y.loc[7:] = 1e9                                         # change only the future
    assert scale_stats(y, origin=6) == before


def test_missing_values_are_skipped_not_filled():
    y = series([10, 20, np.nan, 40, 13, 21, 30, 44])
    # pair (7, 3) is lost -> differences 3, 1, 4 -> MAE = 8/3
    mae, _, pairs = scale_stats(y, origin=8)
    assert pairs == 3 and mae == pytest.approx(8 / 3)
    # forecast for key 11 (h = 3 from origin 8) looks up key 7 = 30; key 3 being NaN never matters
    assert seasonal_naive(y, origin=8)[2] == 30
    # if the look-up quarter is missing, the forecast is missing (no silent fill)
    y.loc[7] = np.nan
    assert np.isnan(seasonal_naive(y, origin=8)[2])


def synthetic_panel():
    # Same seasonal shape every year, +2 per quarter per year: every seasonal difference is exactly 2.
    keys = range(quarter_key("2011Q1"), quarter_key("2017Q4") + 1)
    rows = [("TEST", "USD", "revenue", k, 100 + 10 * ((k - 1) % 4) + 2 * ((k - 1) // 4 - 2011))
            for k in keys]
    return pd.DataFrame(rows, columns=["symbol", "currency", "measure", "quarter_key", "value"])


def test_backtest_hand_calculated_mase_is_one():
    # scale = 2 and every out-of-sample error = 2 -> each scaled error = 1 -> MASE = 1.
    # sigma (RMS) = 2 -> 80% half-width = 1.2816 * 2 = 2.56 > 2 -> every actual covered.
    bt = backtest(synthetic_panel())
    m = mase_table(bt).iloc[0]
    # origins 2015Q4..2017Q3 = 8; the last quarter is 2017Q4, so 5 origins x 4 + 3 + 2 + 1 = 26 forecasts
    assert bt["origin"].nunique() == 8 and len(bt) == 26
    assert m["mase"] == pytest.approx(1.0) and m["coverage"] == 1.0


def test_forecast_for_a_target_is_the_same_at_every_horizon():
    # For h <= 4 the seasonal-naive forecast of quarter t is always y(t - 4), whatever the origin.
    bt = backtest(synthetic_panel())
    assert bt.groupby("target")["forecast"].nunique().max() == 1


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("baseline") / "test.duckdb"
    run(db_path=path)
    return path


def test_real_series_grid_and_exclusions(db):
    s = load_series(db)
    assert s[["symbol", "measure"]].drop_duplicates().shape[0] == 46
    assert len(s) == 3506 and s["value"].notna().sum() == 3400
    tsm_2008 = s[(s["symbol"] == "TSM") & (s["quarter_key"] == quarter_key("2008Q4"))]
    assert tsm_2008["value"].isna().all()                  # exclude_from_modelling respected


def test_real_forecast_equals_same_quarter_last_year(db):
    fc = forecast_next(load_series(db))
    assert len(fc) == 23 * 2 * 4
    nvda = fc[(fc["symbol"] == "NVDA") & (fc["measure"] == "revenue") & (fc["h"] == 1)].iloc[0]
    assert nvda["target_quarter"] == "2025Q4"
    assert nvda["forecast"] == pytest.approx(39_331_000_000)   # NVDA revenue, calendar 2024Q4