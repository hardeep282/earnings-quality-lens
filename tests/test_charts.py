

"""Test for the action-titled chart (step S1.2).  Run:  python -m pytest -q

Builds the pipeline and the baseline into a temporary database, then checks that the chart's
title states the number computed from Gold (not a hard-coded one).
"""
from __future__ import annotations

import pytest

from src.baseline import backtest, forecast_next, load_series, mase_table, write_gold
from src.charts import coverage_chart, load_coverage
from src.pipeline import run


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("charts") / "test.duckdb"
    run(db_path=path)
    series = load_series(path)
    write_gold(forecast_next(series), mase_table(backtest(series)), db_path=path)
    return path


def test_title_states_the_computed_insight(db):
    cov = load_coverage(db)
    fig = coverage_chart(db)
    title = fig.get_suptitle()
    assert f"only {cov['revenue'].mean():.0%} of the time" in title     # 44% on this CSV
    assert title.endswith("(NVDA 11%)")
    assert len(fig.axes[0].get_yticklabels()) == 23