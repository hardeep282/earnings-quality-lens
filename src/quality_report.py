

"""Quality scorecard, readiness score and cleaning plan -> docs/02_data_quality_report.md (Phase 2, step 2.5).

Also writes row-level flags to data/interim/row_flags.csv for the Silver layer (Phase 5).
Run from the project root:  python -m src.quality_report
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_dictionary import to_markdown_table
from src.data_load import KEY_COLS, load_raw
from src.quality_checks import identity_checks, not_whole_thousands, repeated_quarters
from src.quality_context import calendar_quarter, missingness_types
from src.reference import FINANCIALS

REPORT_PATH = Path("docs/02_data_quality_report.md")
FLAGS_PATH = Path("data/interim/row_flags.csv")

CORE = ["totalRevenue", "costOfRevenue", "grossProfit", "operatingIncome",
        "incomeBeforeTax", "incomeTaxExpense", "netIncome"]
NON_NEGATIVE = ["totalRevenue", "costOfRevenue", "researchAndDevelopment", "sellingGeneralAndAdministrative"]
# Weights sum to 100. Consistency and accuracy weigh most: they decide whether KPIs are trustworthy.
WEIGHTS = {"Completeness": 20, "Uniqueness": 10, "Validity": 15,
           "Consistency": 20, "Timeliness": 10, "Accuracy (proxy)": 25}
GO, CONDITIONAL = 85, 70   # readiness bands (house rule, stated as an assumption)


def row_flags(df: pd.DataFrame) -> pd.DataFrame:
    """One row per company-quarter with the quality flags Silver will act on."""
    f = df[KEY_COLS].copy()
    f["calendar_quarter"] = calendar_quarter(df["fiscalDateEnding"]).astype(str)
    f["is_financial"] = df["symbol"].isin(FINANCIALS)
    f["is_derived"] = not_whole_thousands(df)
    f["is_repeated"] = False
    rep = repeated_quarters(df)
    f.loc[f.set_index(KEY_COLS).index.isin(rep.set_index(KEY_COLS).index), "is_repeated"] = True
    f["invalid_negative"] = (df[NON_NEGATIVE] < 0).any(axis=1) & ~f["is_financial"]
    f["exclude_from_modelling"] = f["is_derived"] | f["is_repeated"]
    return f


def scorecard(df: pd.DataFrame, flags: pd.DataFrame) -> pd.DataFrame:
    non_fin = ~flags["is_financial"]
    rev = df["totalRevenue"].abs()
    gp_gap = (df["grossProfit"] - (df["totalRevenue"] - df["costOfRevenue"])).abs() / rev
    oi_gap = (df["operatingIncome"] - (df["grossProfit"] - df["operatingExpenses"])).abs() / rev
    testable = non_fin & gp_gap.notna() & oi_gap.notna()
    both_ok = ((gp_gap <= 0.01) & (oi_gap <= 0.01))[testable].mean()
    latest = calendar_quarter(df.groupby("symbol")["fiscalDateEnding"].max())
    rows = [
        ("Completeness", 100 * df[CORE].notna().to_numpy().mean(),
         "Share of non-missing cells in the 7 core income-statement columns"),
        ("Uniqueness", 100 * (1 - df.duplicated(KEY_COLS).mean()),
         "Share of rows unique on (symbol, fiscalDateEnding)"),
        ("Validity", 100 * (1 - flags["invalid_negative"].mean()),
         "Share of rows with no impossible negatives (financials judged separately)"),
        ("Consistency", 100 * both_ok,
         "Non-financial rows where BOTH the gross-profit and operating-income identities hold within 1% of revenue"),
        ("Timeliness", 100 * (latest == latest.max()).mean(),
         f"Share of companies reporting the latest quarter ({latest.max()})"),
        ("Accuracy (proxy)", 100 * (1 - flags["exclude_from_modelling"].mean()),
         "Share of rows that look company-reported (not vendor-derived or copied); no external tie-out possible"),
    ]
    sc = pd.DataFrame(rows, columns=["dimension", "score_pct", "how_measured"])
    sc["score_pct"] = sc["score_pct"].round(1)
    sc["weight"] = sc["dimension"].map(WEIGHTS)
    return sc[["dimension", "score_pct", "weight", "how_measured"]]


CLEANING_PLAN = [
    ("Drop 5 fully empty columns", "investmentIncomeNet, nonInterestIncome, depreciation, interestAndDebtExpense, comprehensiveIncomeNetOfTax", "Silver"),
    ("Drop duplicate column", "costofGoodsAndServicesSold (100% equal to costOfRevenue)", "Silver"),
    ("Fill 2 blank currencies", "PLTR 2019-03/06 -> USD (all other PLTR rows are USD); logged", "Silver"),
    ("Add calendar_quarter", "Midpoint rule (period end - 45 days); 0 collisions", "Silver"),
    ("Flag vendor-derived and copied quarters", "is_derived (28 rows), is_repeated (4 rows); excluded from modelling, kept for context", "Silver"),
    ("Financials rule", "No gross margin for JPM, BRK-B, V, MA; negative COGS accepted for them", "Gold KPIs"),
    ("Operating income source of truth", "Use reported operatingIncome; never rebuild from grossProfit - operatingExpenses", "Gold KPIs"),
    ("R&D and SG&A", "Missing = 'not applicable', never 0; SG&A intensity compared within company only", "Gold KPIs"),
    ("Effective tax rate", "TTM, only where TTM pre-tax income > 0", "Gold KPIs"),
    ("Interest columns", "Excluded from long-run analysis (coverage depends on time)", "Gold KPIs"),
    ("Currency", "Ratios and growth within company; cross-company totals use USD reporters only", "Gold KPIs"),
]


def build_report(df, flags, sc, readiness, band, ident, miss) -> str:
    plan = pd.DataFrame(CLEANING_PLAN, columns=["action", "detail", "layer"])
    miss_short = miss[["column", "missing_rows", "V_company", "V_year", "type"]]
    return "\n\n".join([
        "# Phase 2 — Data Quality Report",
        "> Generated by `src/quality_report.py`. Do not edit by hand; re-run the script.",
        f"**Dataset:** `corporate_income_statement.csv` · {len(df):,} rows · {df['symbol'].nunique()} companies · "
        "SHA-256 `0898c7c5…61da30` · as of calendar 2025Q3",
        f"## Readiness: **{readiness:.1f} / 100 → {band}**",
        f"Bands (house rule): ≥ {GO} go · {CONDITIONAL}–{GO} conditional (go with documented exclusions) · < {CONDITIONAL} no-go.",
        "## Scorecard (DAMA UK six dimensions)",
        to_markdown_table(sc),
        "## Accounting identities",
        to_markdown_table(ident),
        "## Missingness types (Rubin 1976; Cramér's V against company and year)",
        to_markdown_table(miss_short),
        "## Row flags",
        f"- Vendor-derived rows (values not in whole thousands): {int(flags['is_derived'].sum())}\n"
        f"- Copied quarters (identical to previous quarter): {int(flags['is_repeated'].sum())}\n"
        f"- Excluded from modelling (either flag): {int(flags['exclude_from_modelling'].sum())}\n"
        f"- Written to `{FLAGS_PATH.as_posix()}` for the Silver layer",
        "## Cleaning plan",
        to_markdown_table(plan),
        "## Limits",
        "- **Accuracy is a proxy.** Without an external source (CSV-only rule) we cannot prove figures match filings; "
        "internal identities and derived-row detection are the best available evidence.\n"
        "- Readiness weights and bands are a stated house rule, not an industry standard.",
    ]) + "\n"


if __name__ == "__main__":
    df = load_raw()
    flags = row_flags(df)
    sc = scorecard(df, flags)
    readiness = (sc["score_pct"] * sc["weight"]).sum() / sc["weight"].sum()
    band = "GO" if readiness >= GO else "CONDITIONAL GO" if readiness >= CONDITIONAL else "NO-GO"
    if band == "GO" and flags["exclude_from_modelling"].any():
        band = "GO with documented exclusions"
    FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    flags.to_csv(FLAGS_PATH, index=False, lineterminator="\n")
    report = build_report(df, flags, sc, readiness, band, identity_checks(df), missingness_types(df))
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(sc[["dimension", "score_pct", "weight"]].to_string(index=False))
    print(f"\nReadiness score : {readiness:.1f} / 100 -> {band}")
    print(f"Excluded rows   : {int(flags['exclude_from_modelling'].sum())} of {len(flags)}")
    print(f"Written         : {REPORT_PATH} and {FLAGS_PATH}")