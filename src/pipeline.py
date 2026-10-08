"""Run the medallion pipeline: every sql/pipeline/*.sql file in order, into one DuckDB database.

Run from the project root:  python -m src.pipeline
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

from src.data_load import EXPECTED_SHA256, RAW_PATH, sha256_of
from src.kpis import MIN_BASE_MARGIN
from src.quality_checks import TOL
from src.reference import (
    BUSINESS_GROUP,
    FINANCIALS,
    KPI_CAUTION,
    MANUAL_EXCLUSIONS,
    NON_US,
)

load_dotenv()
DB_PATH = Path(os.getenv("DUCKDB_PATH", "data/processed/earnings.duckdb"))
SQL_DIR = Path("sql/pipeline")


def seed_reference(con: duckdb.DuckDBPyConnection) -> None:
    """Write src/reference.py into ref.* tables, so SQL and Python share one source of truth."""
    company = pd.DataFrame({"symbol": list(BUSINESS_GROUP), "business_group": list(BUSINESS_GROUP.values())})
    company["is_financial"] = company["symbol"].isin(FINANCIALS)
    company["is_non_us"] = company["symbol"].isin(NON_US)
    company["kpi_caution"] = company["symbol"].map(KPI_CAUTION)
    exclusions = pd.DataFrame(MANUAL_EXCLUSIONS, columns=["symbol", "first_date", "last_date", "reason"])
    exclusions[["first_date", "last_date"]] = exclusions[["first_date", "last_date"]].apply(pd.to_datetime)
    parameters = pd.DataFrame({"name": ["identity_tolerance", "min_base_margin"],
                               "value": [TOL, MIN_BASE_MARGIN]})
    con.execute("CREATE SCHEMA IF NOT EXISTS ref")
    for name, frame in [("company", company), ("manual_exclusion", exclusions), ("kpi_parameter", parameters)]:
        con.register("seed_df", frame)
        con.execute(f"CREATE OR REPLACE TABLE ref.{name} AS SELECT * FROM seed_df")
        con.unregister("seed_df")


def run(db_path: Path = DB_PATH, raw_path: Path = RAW_PATH) -> list[str]:
    """Verify the raw file, seed reference tables, then execute each SQL file in name order."""
    actual = sha256_of(raw_path)
    if actual != EXPECTED_SHA256:
        raise ValueError(f"Fingerprint mismatch: expected {EXPECTED_SHA256}, got {actual}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(SQL_DIR.glob("*.sql"))
    with duckdb.connect(str(db_path)) as con:
        con.execute("SET VARIABLE raw_path = ?", [raw_path.as_posix()])
        con.execute("SET VARIABLE raw_sha256 = ?", [actual])
        con.execute("SET VARIABLE tol = ?", [TOL])
        seed_reference(con)
        for f in files:
            con.execute(f.read_text(encoding="utf-8"))
    return [f.name for f in files]


def table_summary(db_path: Path = DB_PATH) -> list[tuple]:
    """(schema.table, rows, columns) for every table and view in the database."""
    with duckdb.connect(str(db_path), read_only=True) as con:
        objects = con.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema <> 'main' ORDER BY table_schema, table_name").fetchall()
        out = []
        for schema, name in objects:
            rows = con.execute(f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
            cols = con.execute("SELECT count(*) FROM information_schema.columns "
                               "WHERE table_schema = ? AND table_name = ?", [schema, name]).fetchone()[0]
            out.append((f"{schema}.{name}", rows, cols))
        return out


if __name__ == "__main__":
    ran = run()
    print(f"Fingerprint OK : {EXPECTED_SHA256[:16]}...")
    print(f"Database       : {DB_PATH.as_posix()}")
    print(f"SQL files run  : {', '.join(ran)}")
    print("\nObject                          rows  columns")
    for name, rows, cols in table_summary():
        print(f"{name:<30}{rows:>6}{cols:>9}")
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        last = con.execute("SELECT row_count, sha256 FROM bronze.load_log ORDER BY loaded_at DESC LIMIT 1").fetchone()
        types = con.execute("SELECT DISTINCT data_type FROM information_schema.columns "
                            "WHERE table_schema = 'bronze' AND table_name = 'income_statement'").fetchall()
        none_text = con.execute("SELECT count(*) FROM bronze.income_statement WHERE totalRevenue = 'None' "
                                "OR operatingIncome = 'None'").fetchone()[0]
    print(f"\nLatest load    : {last[0]} rows, sha256 {last[1][:16]}...")
    print(f"Bronze types   : {', '.join(t[0] for t in types)} (raw text, nothing interpreted yet)")
    print(f"'None' kept    : {none_text} rows still hold the literal text 'None' in revenue or operating income")