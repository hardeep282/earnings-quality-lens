"""Reconcile the DuckDB pipeline against the tested Python code, layer by layer.

Run from the project root (after python -m src.pipeline):  python -m src.reconcile
"""
from __future__ import annotations

import duckdb
import pandas as pd

from src.data_load import load_raw
from src.kpis import build, input_validity
from src.pipeline import DB_PATH
from src.quality_report import row_flags

# silver column -> (python frame, python column)
FLAG_MAP = {
    "is_derived_row": ("row", "is_derived"), "is_repeated": ("row", "is_repeated"),
    "exclude_from_modelling": ("row", "exclude_from_modelling"), "is_financial": ("row", "is_financial"),
    "is_derived_input": ("kpi", "is_derived"), "stale_revenue": ("kpi", "stale_revenue"),
    "stale_oi": ("kpi", "stale_oi"), "is_missing_input": ("kpi", "is_missing"),
    "is_manual": ("kpi", "is_manual"), "input_valid": ("kpi", "input_valid"),
}


def silver_vs_python(db_path=DB_PATH) -> pd.DataFrame:
    """Row-by-row comparison of every Silver flag with the Phase 2/3 Python flags."""
    with duckdb.connect(str(db_path), read_only=True) as con:
        s = con.execute("SELECT * FROM silver.income_statement").df()
    raw = load_raw()
    py = {"row": row_flags(raw), "kpi": input_validity(raw)}
    key = ["symbol", "fiscalDateEnding"]
    s = s.rename(columns={"fiscal_date": "fiscalDateEnding"})
    s["fiscalDateEnding"] = pd.to_datetime(s["fiscalDateEnding"])
    rows = []
    for col, (frame, pcol) in FLAG_MAP.items():
        left = s[key + [col]].rename(columns={col: "sql"})
        right = py[frame][key + [pcol]].rename(columns={pcol: "py"})
        m = left.merge(right, on=key, how="outer", indicator=True)
        both = m["_merge"] == "both"
        sql_flag, py_flag = m["sql"].fillna(False).astype(bool), m["py"].fillna(False).astype(bool)
        rows.append({"flag": col, "silver_true": int(sql_flag.sum()), "python_true": int(py_flag.sum()),
                     "rows_matched": int(both.sum()), "rows_differ": int((sql_flag != py_flag)[both].sum())})
    q = calendar_check(s, py["row"])
    rows.append({"flag": "calendar_quarter", "silver_true": len(s), "python_true": len(py["row"]),
                 "rows_matched": len(s), "rows_differ": q})
    return pd.DataFrame(rows)


def calendar_check(s: pd.DataFrame, flags: pd.DataFrame) -> int:
    m = s[["symbol", "fiscalDateEnding", "calendar_quarter"]].merge(
        flags[["symbol", "fiscalDateEnding", "calendar_quarter"]], on=["symbol", "fiscalDateEnding"],
        suffixes=("_sql", "_py"))
    return int((m["calendar_quarter_sql"] != m["calendar_quarter_py"]).sum())


def gold_vs_python(db_path=DB_PATH) -> pd.DataFrame:
    """Compare gold.north_star and gold.north_star_lfl with the tested Phase 3 pandas North Star."""
    with duckdb.connect(str(db_path), read_only=True) as con:
        g = con.execute("SELECT * FROM gold.north_star").df()
        gl = con.execute("SELECT * FROM gold.north_star_lfl").df()
    _, ns, lfl = build()
    ns = ns.assign(calendar_quarter=ns["calendar_quarter"].astype(str))
    m = g.merge(ns, on=["symbol", "calendar_quarter"], how="outer", suffixes=("_sql", "_py"), indicator=True)
    both = m[m["_merge"] == "both"]
    rows = [("company-quarter slots", len(g), len(ns), int((m["_merge"] != "both").sum()))]
    for col in ["ttm_oi", "ttm_margin", "margin_change_pp", "ns_growth"]:
        a, b = both[f"{col}_sql"], both[f"{col}_py"]
        differ = int(((a - b).abs() > 1e-9 * b.abs().clip(lower=1)).sum() + (a.isna() != b.isna()).sum())
        rows.append((col, int(a.notna().sum()), int(b.notna().sum()), differ))
    for col in ["ns_status", "quality_quadrant", "caution"]:
        rows.append((col, len(both), len(both), int((both[f"{col}_sql"] != both[f"{col}_py"]).sum())))
    lm = gl.merge(lfl.assign(calendar_quarter=lfl["calendar_quarter"].astype(str)),
                  on="calendar_quarter", how="outer", suffixes=("_sql", "_py"), indicator=True)
    lb = lm[lm["_merge"] == "both"]
    rows.append(("LFL quarters", len(gl), len(lfl), int((lm["_merge"] != "both").sum())))
    rows.append(("LFL companies", int(lb["companies_sql"].sum()), int(lb["companies_py"].sum()),
                 int((lb["companies_sql"] != lb["companies_py"]).sum())))
    lg = (lb["ns_growth_sql"] - lb["ns_growth_py"]).abs() > 1e-9
    rows.append(("LFL ns_growth", int(lb["ns_growth_sql"].notna().sum()),
                 int(lb["ns_growth_py"].notna().sum()), int(lg.sum())))
    return pd.DataFrame(rows, columns=["measure", "sql_values", "python_values", "rows_differ"])


def row_counts(db_path=DB_PATH) -> pd.DataFrame:
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute("""
            SELECT 'csv (pandas)' AS layer, ? AS rows
            UNION ALL SELECT 'bronze.income_statement', count(*) FROM bronze.income_statement
            UNION ALL SELECT 'silver.income_statement', count(*) FROM silver.income_statement
            UNION ALL SELECT 'gold.fact_quarter', count(*) FROM gold.fact_quarter
        """, [len(load_raw())]).df()


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    print("== Row-count reconciliation ==")
    print(row_counts().to_string(index=False))
    print("\n== Silver flags vs tested Python code (row by row) ==")
    print(silver_vs_python().to_string(index=False))
    print("\n== Gold North Star views vs tested Python (Phase 3) ==")
    print(gold_vs_python().to_string(index=False))