

"""Smoke test for the Streamlit app (step S1.3), run headless with Streamlit's AppTest.

Run:  python -m pytest -q
It uses your working data/processed/earnings.duckdb (read-only) and is skipped if that has not been
built yet (python -m src.pipeline, then python -m src.baseline).
"""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from src.pipeline import DB_PATH

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="Gold not built yet")


def test_app_renders_without_errors():
    at = AppTest.from_file("../app/streamlit_app.py", default_timeout=60).run()
    assert not at.exception
    assert at.title[0].value == "Earnings Quality Lens"
    assert "Not investment advice" in at.warning[0].value
    assert at.metric[0].value == "+16.7%"                      # 2025Q3 like-for-like USD, Phase 3
    assert len(at.dataframe[0].value) == 23                   # one latest row per company


def test_company_selector_switches_the_forecast():
    at = AppTest.from_file("../app/streamlit_app.py", default_timeout=60).run()
    assert at.selectbox[0].value == "NVDA"
    nvda = at.dataframe[1].value
    assert nvda.shape == (4, 5)
    assert nvda["Revenue"].iloc[0] == pytest.approx(39.331)       # NVDA 2024Q4 revenue, USD bn
    at.selectbox[0].select("TSM").run()
    assert not at.exception
    assert not at.dataframe[1].value.equals(nvda)                  # the table followed the selection