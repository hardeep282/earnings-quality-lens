

"""Tests for the Phase 2 loader and quality helpers.  Run:  python -m pytest -q"""
from __future__ import annotations

import shutil

import pandas as pd
import pytest

from src.data_load import KEY_COLS, RAW_PATH, load_raw
from src.quality_context import calendar_quarter, cramers_v


def test_raw_file_loads_with_expected_shape_and_unique_grain():
    df = load_raw()
    assert df.shape == (1750, 27)
    assert not df.duplicated(KEY_COLS).any()
    assert df["symbol"].nunique() == 23


def test_fingerprint_guard_rejects_a_modified_file(tmp_path):
    tampered = tmp_path / "tampered.csv"
    shutil.copy(RAW_PATH, tampered)
    with tampered.open("ab") as handle:
        handle.write(b"\n")                      # change a single byte
    with pytest.raises(ValueError, match="Fingerprint mismatch"):
        load_raw(tampered)


def test_only_none_and_blank_become_missing(tmp_path):
    sample = tmp_path / "sample.csv"
    sample.write_text("symbol,fiscalDateEnding,reportedCurrency,totalRevenue\n"
                      "NA,2025-03-31,USD,100\n"
                      "XYZ,2025-03-31,None,None\n", encoding="utf-8")
    df = load_raw(sample, verify=False)
    assert df.loc[0, "symbol"] == "NA"           # a real ticker survives
    assert pd.isna(df.loc[1, "reportedCurrency"]) and pd.isna(df.loc[1, "totalRevenue"])


@pytest.mark.parametrize("period_end, expected", [
    ("2025-01-31", "2024Q4"),   # NVDA-style quarter (Nov-Jan)
    ("2025-02-28", "2025Q1"),   # COST/ORCL-style quarter (Dec-Feb)
    ("2025-03-31", "2025Q1"),   # calendar quarter
    ("2025-10-31", "2025Q3"),   # Aug-Oct
])
def test_calendar_quarter_midpoint_rule(period_end, expected):
    result = calendar_quarter(pd.Series(pd.to_datetime([period_end])))
    assert str(result.iloc[0]) == expected


def test_cramers_v_is_one_for_perfect_and_zero_for_no_association():
    groups = pd.Series(list("AABB") * 5)
    assert cramers_v(groups == "A", groups) == pytest.approx(1.0)
    assert cramers_v(pd.Series([True, False] * 10), pd.Series(list("AABB") * 5)) == pytest.approx(0.0)