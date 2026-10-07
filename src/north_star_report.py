

"""North Star KPI spec card -> docs/03_north_star.md, with a SQL (DuckDB) tie-out to pandas (Phase 3, step 3.4).

Run from the project root:  python -m src.north_star_report
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.data_dictionary import to_markdown_table
from src.kpis import MIN_BASE_MARGIN, build
from src.reference import KPI_CAUTION, MANUAL_EXCLUSIONS

OUT_PATH = Path("docs/03_north_star.md")

# Runs against kpi_inputs(symbol, calendar_quarter, q_idx, total_revenue, operating_income, input_valid).
# q_idx = year * 4 + quarter, so RANGE windows see gaps; valid_quarters = 4 enforces D2.
SQL_NORTH_STAR = """
WITH ttm AS (
    SELECT symbol, calendar_quarter, q_idx,
           SUM(CASE WHEN input_valid THEN operating_income END) OVER w AS ttm_oi,
           SUM(CASE WHEN input_valid THEN total_revenue END)    OVER w AS ttm_revenue,
           COUNT(CASE WHEN input_valid THEN 1 END)              OVER w AS valid_quarters
    FROM kpi_inputs
    WINDOW w AS (PARTITION BY symbol ORDER BY q_idx RANGE BETWEEN 3 PRECEDING AND CURRENT ROW)
),
ttm_ok AS (
    SELECT symbol, calendar_quarter, q_idx, ttm_oi, ttm_revenue FROM ttm WHERE valid_quarters = 4
)
SELECT c.symbol, c.calendar_quarter,
       c.ttm_oi, b.ttm_oi AS base_ttm_oi,
       c.ttm_oi / c.ttm_revenue AS ttm_margin,
       CASE WHEN b.ttm_oi > 0 AND b.ttm_oi / b.ttm_revenue >= ?
            THEN c.ttm_oi / b.ttm_oi - 1 END AS ns_growth
FROM ttm_ok AS c
LEFT JOIN ttm_ok AS b ON b.symbol = c.symbol AND b.q_idx = c.q_idx - 4
ORDER BY c.symbol, c.q_idx
""".strip()

DAX_NORTH_STAR = """
-- Not executed here; validated in Phase 11. Fact grain = company x calendar quarter;
-- 'Calendar'[QuarterIndex] = year * 4 + quarter. Avoids DATESINPERIOD (fiscal -> calendar mapping is done upstream).
TTM OI :=
VAR q = MAX ( 'Calendar'[QuarterIndex] )
VAR win = CALCULATETABLE ( Facts, REMOVEFILTERS ( 'Calendar' ),
          'Calendar'[QuarterIndex] > q - 4, 'Calendar'[QuarterIndex] <= q, Facts[input_valid] = TRUE () )
RETURN IF ( COUNTROWS ( win ) = 4, SUMX ( win, Facts[operating_income] ) )

TTM OI Base :=
VAR q = MAX ( 'Calendar'[QuarterIndex] ) - 4
VAR win = CALCULATETABLE ( Facts, REMOVEFILTERS ( 'Calendar' ),
          'Calendar'[QuarterIndex] > q - 4, 'Calendar'[QuarterIndex] <= q, Facts[input_valid] = TRUE () )
RETURN IF ( COUNTROWS ( win ) = 4, SUMX ( win, Facts[operating_income] ) )

-- TTM Revenue Base: same as TTM OI Base, summing Facts[total_revenue]
North Star Growth :=
VAR base = [TTM OI Base]
VAR base_margin = DIVIDE ( base, [TTM Revenue Base] )
RETURN IF ( base > 0 && base_margin >= 0.02, DIVIDE ( [TTM OI], base ) - 1 )
""".strip()

EXCEL_NORTH_STAR = """
Table tblKPI with columns: symbol | q_idx | operating_income | total_revenue | input_valid (TRUE/FALSE)
Not executed here; validated in Phase 4.

TTM OI (row r):
=IF(COUNTIFS([symbol],[@symbol],[q_idx],">"&[@q_idx]-4,[q_idx],"<="&[@q_idx],[input_valid],TRUE)=4,
    SUMIFS([operating_income],[symbol],[@symbol],[q_idx],">"&[@q_idx]-4,[q_idx],"<="&[@q_idx],[input_valid],TRUE),"")

Base TTM OI: same formula with [@q_idx]-4 in place of [@q_idx]
North Star growth:
=IF(AND([@base_ttm_oi]<>"",[@base_ttm_oi]>0,[@base_ttm_oi]/[@base_ttm_revenue]>=0.02),[@ttm_oi]/[@base_ttm_oi]-1,"")
""".strip()


def kpi_inputs(valid: pd.DataFrame) -> pd.DataFrame:
    """Validated inputs in the shape the SQL expects (the future Silver-layer table)."""
    cq = valid["calendar_quarter"]
    return pd.DataFrame({
        "symbol": valid["symbol"],
        "calendar_quarter": cq.astype(str),
        "q_idx": cq.dt.year * 4 + cq.dt.quarter,
        "total_revenue": valid["totalRevenue"],
        "operating_income": valid["operatingIncome"],
        "input_valid": valid["input_valid"],
    })


def sql_north_star(valid: pd.DataFrame) -> pd.DataFrame:
    con = duckdb.connect()
    con.register("kpi_inputs", kpi_inputs(valid))
    return con.execute(SQL_NORTH_STAR, [MIN_BASE_MARGIN]).df()


def tie_out(ns: pd.DataFrame, sql: pd.DataFrame) -> pd.DataFrame:
    """Compare the pandas and SQL implementations on counts and values."""
    p = ns[ns["ttm_oi"].notna()].assign(calendar_quarter=lambda d: d["calendar_quarter"].astype(str))
    m = p.merge(sql, on=["symbol", "calendar_quarter"], how="outer", suffixes=("_pandas", "_sql"),
                indicator=True)
    both = m["_merge"] == "both"
    growth_diff = (m.loc[both, "ns_growth_pandas"] - m.loc[both, "ns_growth_sql"]).abs().max()
    same_nulls = (m.loc[both, "ns_growth_pandas"].isna() == m.loc[both, "ns_growth_sql"].isna()).all()
    rows = [
        ("Valid TTM values", len(p), len(sql)),
        ("Defined North Star values", int(p["ns_growth"].notna().sum()), int(sql["ns_growth"].notna().sum())),
        ("Rows in only one version", int((~both).sum()), int((~both).sum())),
        ("Same rows undefined", "yes" if same_nulls else "NO", "yes" if same_nulls else "NO"),
        ("Max absolute growth difference", f"{growth_diff:.1e}", f"{growth_diff:.1e}"),
    ]
    return pd.DataFrame(rows, columns=["check", "pandas", "sql"])


def level_breaks(valid: pd.DataFrame) -> pd.DataFrame:
    """Review list: revenue changing more than 3x (or below 1/3) in a single quarter."""
    v = valid.sort_values(["symbol", "fiscalDateEnding"])
    ratio = v["totalRevenue"] / v.groupby("symbol")["totalRevenue"].shift(1)
    prev_valid = v.groupby("symbol")["input_valid"].shift(1, fill_value=True)
    hit = v[(ratio > 3) | (ratio < 1 / 3)].assign(qoq_ratio=ratio.round(2), prev_valid=prev_valid)
    handled = pd.Series("kept: review in Phase 6", index=hit.index)
    handled[hit["symbol"].isin(KPI_CAUTION)] = "caution flag (D7)"
    handled[~hit["prev_valid"]] = "previous quarter excluded (D3)"
    handled[~hit["input_valid"]] = "excluded input (D3)"
    hit = hit.assign(fiscal_date=hit["fiscalDateEnding"].dt.date.astype(str), handling=handled)
    return hit[["symbol", "fiscal_date", "qoq_ratio", "handling"]]


def pct(x: float) -> str:
    return "" if pd.isna(x) else f"{100 * x:.1f}"


def build_markdown(valid, ns, lfl, sql_tie, breaks) -> str:
    flags = ["is_repeated", "is_derived", "stale_revenue", "stale_oi", "is_missing", "is_manual"]
    status = ns["ns_status"].value_counts().rename_axis("ns_status").reset_index(name="calendar_slots")
    latest = ns[ns["ttm_oi"].notna()].groupby("symbol").tail(1).sort_values("ns_growth", ascending=False)
    latest_t = pd.DataFrame({
        "symbol": latest["symbol"], "calendar_quarter": latest["calendar_quarter"].astype(str),
        "growth_pct": latest["ns_growth"].map(pct), "ttm_margin_pct": latest["ttm_margin"].map(pct),
        "margin_change_pp": latest["margin_change_pp"].round(2), "quadrant": latest["quality_quadrant"],
        "caution": latest["caution"].map(lambda s: "yes" if s else ""),
    })
    lfl_t = lfl.tail(8).assign(
        calendar_quarter=lambda d: d["calendar_quarter"].astype(str),
        growth_pct=lambda d: d["ns_growth"].map(pct), ttm_margin_pct=lambda d: d["ttm_margin"].map(pct),
        margin_change_pp=lambda d: d["margin_change_pp"].round(2),
    )[["calendar_quarter", "companies", "growth_pct", "ttm_margin_pct", "margin_change_pp"]]
    q3 = lfl.iloc[-1]
    naive = ns[(ns["calendar_quarter"] == lfl["calendar_quarter"].iloc[-1])
               & ns["ns_growth"].notna() & ~ns["symbol"].isin(["TSM", "BABA"])]["ns_growth"].mean()
    stale = valid[valid["stale_oi"] | valid["stale_revenue"]]
    stale_t = pd.DataFrame({"symbol": stale["symbol"],
                            "fiscal_date": stale["fiscalDateEnding"].dt.date.astype(str),
                            "stale_column": stale["stale_oi"].map({True: "operatingIncome", False: "totalRevenue"})})
    manual_t = pd.DataFrame(MANUAL_EXCLUSIONS, columns=["symbol", "from", "to", "reason"])

    card = pd.DataFrame([
        ("Name", "North Star: TTM operating-income growth"),
        ("Business question", "Is this company's core business profit growing, year on year?"),
        ("Decision it serves", "Deep-dive priority list within 48 h of earnings (Head of Research, fictional client)"),
        ("Formula", "Σ operatingIncome(q−3…q) / Σ operatingIncome(q−7…q−4) − 1"),
        ("Inputs (exact columns)", ("`operatingIncome`, `totalRevenue` (guardrail), `fiscalDateEnding`, `symbol`; "
                                   "validity also reads `grossProfit`, `costOfRevenue`, `operatingExpenses`, `netIncome`")),
        ("Derivability tag", "Derived (computed from existing columns)"),
        ("Grain", "One value per company × calendar quarter (midpoint rule: fiscal end − 45 days)"),
        ("Currency", "Reported currency, within company (≈ constant-currency for TSM, BABA)"),
        ("Additivity", "Non-additive ratio: aggregate by summing TTM operating income, then dividing (D6)"),
        ("Direction", "Higher is better, but only read together with the guardrail"),
        ("Guardrail", "TTM operating margin = Σ OI / Σ revenue, and its YoY change in percentage points"),
        ("Leading / lagging", "Lagging (reported results); Phase 9 forecasts provide the forward view"),
        ("Target logic", ("No target (external companies). Action threshold [Assumed]: score moves ≥ 1 quintile, "
                         "or margin outside its own 95% forecast interval (finalised Phase 10)")),
        ("Owner", "Analytics lead (definition) · Head of Research (sign-off)"),
        ("Refresh", "Quarterly, on file drop of a new CSV (Phase 13 automation)"),
        ("Governed home", ("`src/kpis.py` now → Gold-layer KPI view in DuckDB (Phase 5) → consumed by Power BI, "
                          "API, MCP and the AI analyst")),
    ], columns=["field", "value"])

    rules = pd.DataFrame([
        ("D1", "Growth of TTM operating income vs the same calendar quarter a year earlier", "—"),
        ("D2", "TTM valid only with 4 consecutive calendar quarters, all inputs valid",
         f"{int(ns['ttm_oi'].notna().sum()):,} valid TTM of {len(ns):,} calendar slots"),
        ("D3", "Input invalid if copied quarter, not whole thousands, stale, missing or manually excluded",
         f"{int((~valid['input_valid']).sum())} company-quarters (" +
         ", ".join(f"{f} {int(valid[f].sum())}" for f in flags) + ")"),
        ("D4", f"No % if base TTM OI ≤ 0 or base margin < {MIN_BASE_MARGIN:.0%}; a status label instead",
         "see status table"),
        ("D5", "Guardrail: TTM margin and YoY change (pp); quality quadrant", "—"),
        ("D6", "Like-for-like USD reporters, ratio of sums, coverage always shown",
         f"{q3['calendar_quarter']}: {pct(q3['ns_growth'])}% (n = {int(q3['companies'])}) vs naive mean {pct(naive)}%"),
        ("D7", "Financials included for OI; caution flag on " + ", ".join(KPI_CAUTION), "—"),
    ], columns=["rule", "definition", "effect [Computed]"])

    return "\n\n".join([
        "# Phase 3 — North Star KPI spec card",
        ("> Generated by `src/north_star_report.py`. Do not edit by hand; re-run the script. "
         "Not investment advice; client fictional."),
        "## 1. Spec card",
        to_markdown_table(card),
        "## 2. KPI tree",
        ("1 + g_OI = (1 + g_revenue) × (margin_t / margin_t−4), so "
         "ln(1 + g_OI) = ln(1 + g_revenue) + ln(margin_t / margin_t−4): growth = volume + efficiency. "
         "The log form is additive (Törnqvist, Vartia & Vartia 1985)."),
        "## 3. Edge-case rules (D1–D7, confirmed by owner 2026-10-08)",
        to_markdown_table(rules),
        "### North Star status across all calendar slots",
        to_markdown_table(status),
        "## 4. Implementations",
        ("**pandas (reference):** `src/kpis.py` → `input_validity` → `ttm_panel` → `north_star` → "
         "`like_for_like`; tested in `tests/test_kpis.py`."),
        "**SQL (DuckDB, executed and tied out):**",
        "```sql\n" + SQL_NORTH_STAR + "\n```",
        "**Tie-out pandas vs SQL [Computed]:**",
        to_markdown_table(sql_tie),
        "**DAX (Power BI):**",
        "```dax\n" + DAX_NORTH_STAR + "\n```",
        "**Excel:**",
        "```text\n" + EXCEL_NORTH_STAR + "\n```",
        "## 5. Headline values [Computed]",
        "### Latest North Star per company",
        to_markdown_table(latest_t),
        "### Like-for-like USD aggregate (last 8 calendar quarters)",
        to_markdown_table(lfl_t),
        "## 6. Data-quality inputs to the KPI",
        "### Stale values (repeat of previous quarter not confirmed by its accounting identity)",
        to_markdown_table(stale_t),
        "### Manual exclusions (governed in `src/reference.py`)",
        to_markdown_table(manual_t),
        "### Level-break review list (revenue ×3 or ÷3 in one quarter)",
        to_markdown_table(breaks),
        "## 7. Known limits",
        ("- Accuracy is a proxy: no external tie-out under the CSV-only rule.\n"
        "- Lagging metric; survivorship bias (23 of today's mega-caps).\n"
        "- TSM TTM operating income is only usable for 2014–2017 and from 2022 (carried-forward Q1 values).\n"
        "- BRK-B revenue and operating income appear to include investment gains [Inferred]: shown with a caution flag.\n"
        "- Aggregate coverage changes when a company lags (AVGO at 2025Q2): always read `companies`.\n"
        "- 2018 contains both a tax change (TCJA) and a revenue-standard change (ASC 606)."),
        "## 8. Sources",
        ("- Amplitude, *North Star Playbook* (metric + inputs + definitions)\n"
        "- Strathern, M. (1997). 'Improving ratings'. *European Review* 5(3), 305–321 (Goodhart's law → guardrail)\n"
        "- Törnqvist, L., Vartia, P. & Vartia, Y. (1985). How should relative changes be measured? "
        "*The American Statistician*. doi:10.1080/00031305.1985.10479385\n"
        "- DuckDB documentation: window functions (RANGE framing)\n"
        "- DAX Guide: DATESINPERIOD (WINDOW preferred; calendar mapping done upstream)"),
    ]) + "\n"


if __name__ == "__main__":
    valid, ns, lfl = build()
    sql = sql_north_star(valid)
    tie = tie_out(ns, sql)
    breaks = level_breaks(valid)
    OUT_PATH.write_text(build_markdown(valid, ns, lfl, tie, breaks), encoding="utf-8", newline="\n")
    print("== Tie-out: pandas vs SQL (DuckDB) ==")
    print(tie.to_string(index=False))
    print(f"\n== Level-break review list: {len(breaks)} rows ==")
    print(breaks.to_string(index=False))
    print(f"\nWritten : {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")