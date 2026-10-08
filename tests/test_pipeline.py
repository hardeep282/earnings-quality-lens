

"""Data tests on the DuckDB medallion pipeline (Phase 5).  Run:  python -m pytest -q

The pipeline is built into a temporary database, so these tests never depend on, or change,
your working data/processed/earnings.duckdb.
"""
from __future__ import annotations

import duckdb
import pytest

from src.pipeline import run
from src.reconcile import gold_vs_python, row_counts, silver_vs_python

NS_STATUSES = ("defined", "no TTM pair", "turned profitable", "loss narrowed",
               "loss widened or flat", "base margin below 2%")


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("pipeline") / "test.duckdb"
    run(db_path=path)
    return path


def scalar(db, sql):
    with duckdb.connect(str(db), read_only=True) as con:
        return con.execute(sql).fetchone()[0]


def test_row_counts_reconcile_across_every_layer(db):
    counts = row_counts(db)["rows"]
    assert counts.nunique() == 1 and counts.iloc[0] == 1750


def test_fact_grain_is_unique_and_keys_not_null(db):
    assert scalar(db, "SELECT count(*) FROM gold.fact_quarter "
                      "WHERE company_key IS NULL OR quarter_key IS NULL") == 0
    assert scalar(db, "SELECT count(*) - count(DISTINCT (company_key, quarter_key)) "
                      "FROM gold.fact_quarter") == 0


def test_dimension_keys_are_unique(db):
    assert scalar(db, "SELECT count(*) - count(DISTINCT company_key) FROM gold.dim_company") == 0
    assert scalar(db, "SELECT count(*) - count(DISTINCT symbol) FROM gold.dim_company") == 0
    assert scalar(db, "SELECT count(*) - count(DISTINCT quarter_key) FROM gold.dim_quarter") == 0


def test_referential_integrity_fact_to_dimensions(db):
    assert scalar(db, "SELECT count(*) FROM gold.fact_quarter f "
                      "ANTI JOIN gold.dim_company d USING (company_key)") == 0
    assert scalar(db, "SELECT count(*) FROM gold.fact_quarter f "
                      "ANTI JOIN gold.dim_quarter q USING (quarter_key)") == 0


def test_date_dimension_has_no_gaps(db):
    assert scalar(db, "SELECT max(quarter_key) - min(quarter_key) + 1 - count(*) FROM gold.dim_quarter") == 0


def test_north_star_status_has_only_accepted_values(db):
    allowed = ", ".join(f"'{s}'" for s in NS_STATUSES)
    assert scalar(db, f"SELECT count(*) FROM gold.north_star WHERE ns_status NOT IN ({allowed})") == 0
    assert scalar(db, "SELECT count(*) FROM gold.north_star "
                      "WHERE (ns_growth IS NULL) <> (ns_status <> 'defined')") == 0


def test_kpi_parameters_are_stored_as_a_table(db):
    # Regression for incident P5.2: views must not depend on session variables
    assert scalar(db, "SELECT value FROM ref.kpi_parameter WHERE name = 'min_base_margin'") == 0.02
    assert scalar(db, "SELECT count(*) FROM gold.north_star WHERE ns_status = 'base margin below 2%'") == 26


def test_silver_flags_equal_tested_python(db):
    assert silver_vs_python(db)["rows_differ"].sum() == 0


def test_gold_north_star_equals_tested_python(db):
    assert gold_vs_python(db)["rows_differ"].sum() == 0


def test_bronze_load_is_logged_with_fingerprint(db):
    assert scalar(db, "SELECT sha256 FROM bronze.load_log ORDER BY loaded_at DESC LIMIT 1").startswith("0898c7c5")