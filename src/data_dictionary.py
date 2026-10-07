


"""Generate the data dictionary (docs/02_data_dictionary.md) from the raw data plus column metadata.

Run from the project root:  python -m src.data_dictionary
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_load import load_raw
from src.reference import BUSINESS_GROUP

OUT_PATH = Path("docs/02_data_dictionary.md")

ADD = "Additive over time; across companies only in the same currency"
# column: (semantic role, additivity, value-chain position, meaning)
COLUMN_META = {
    "symbol": ("ID / dimension", "n/a", "Key", "Stock ticker; with fiscalDateEnding forms the grain"),
    "fiscalDateEnding": ("Date", "n/a", "Key", "Last day of the company's fiscal quarter"),
    "reportedCurrency": ("Dimension", "n/a", "Context", "Currency the figures are reported in"),
    "totalRevenue": ("Measure (flow)", ADD, "1 Revenue", "Sales in the quarter"),
    "costOfRevenue": ("Measure (flow)", ADD, "2 Cost of revenue", "Direct cost of goods/services sold"),
    "costofGoodsAndServicesSold": ("Measure (flow)", ADD, "2 Cost of revenue", "Duplicate of costOfRevenue (to verify)"),
    "grossProfit": ("Measure (flow)", ADD, "3 Gross profit", "Revenue minus cost of revenue"),
    "researchAndDevelopment": ("Measure (flow)", ADD, "4 Operating costs", "R&D spend"),
    "sellingGeneralAndAdministrative": ("Measure (flow)", ADD, "4 Operating costs", "Selling, general & admin (vendor mapping varies)"),
    "operatingExpenses": ("Measure (flow)", ADD, "4 Operating costs", "Total operating expenses"),
    "operatingIncome": ("Measure (flow)", ADD, "5 Operating income", "Profit from the core business"),
    "investmentIncomeNet": ("Measure (flow)", ADD, "6 Non-operating", "Investment income"),
    "netInterestIncome": ("Measure (flow)", ADD, "6 Non-operating", "Interest income minus interest expense"),
    "interestIncome": ("Measure (flow)", ADD, "6 Non-operating", "Interest earned"),
    "interestExpense": ("Measure (flow)", ADD, "6 Non-operating", "Interest paid on debt"),
    "nonInterestIncome": ("Measure (flow)", ADD, "6 Non-operating", "Banks: fee income"),
    "otherNonOperatingIncome": ("Measure (flow)", ADD, "6 Non-operating", "Other non-core items"),
    "depreciation": ("Measure (flow)", ADD, "Add-back", "Depreciation only"),
    "depreciationAndAmortization": ("Measure (flow)", ADD, "Add-back", "Depreciation and amortisation"),
    "incomeBeforeTax": ("Measure (flow)", ADD, "7 Pre-tax income", "Profit before tax"),
    "incomeTaxExpense": ("Measure (flow)", ADD, "8 Tax", "Income tax charge"),
    "interestAndDebtExpense": ("Measure (flow)", ADD, "6 Non-operating", "Interest and debt costs"),
    "netIncomeFromContinuingOperations": ("Measure (flow)", ADD, "9 Net income", "Net income excluding discontinued operations"),
    "comprehensiveIncomeNetOfTax": ("Measure (flow)", ADD, "Other", "Comprehensive income"),
    "ebit": ("Measure (flow)", ADD, "7 EBIT", "Earnings before interest and tax"),
    "ebitda": ("Measure (flow)", ADD, "7 EBITDA", "EBIT plus depreciation and amortisation"),
    "netIncome": ("Measure (flow)", ADD, "9 Net income", "Bottom-line profit"),
}


def profile(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: type, completeness, range and sign, joined to the metadata."""
    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        role, additivity, chain, meaning = COLUMN_META[col]
        row = {
            "column": col, "dtype": str(s.dtype), "role": role, "value_chain": chain,
            "meaning": meaning, "additivity": additivity,
            "non_null": int(s.notna().sum()), "complete_pct": round(100 * s.notna().mean(), 1),
        }
        if pd.api.types.is_numeric_dtype(s) and s.notna().any():
            row["min"] = f"{s.min():,.0f}"
            row["max"] = f"{s.max():,.0f}"
            row["negative_pct"] = round(100 * (s < 0).sum() / s.notna().sum(), 1)
        elif pd.api.types.is_datetime64_any_dtype(s):
            row["min"], row["max"], row["negative_pct"] = str(s.min().date()), str(s.max().date()), ""
        else:
            row["min"] = row["max"] = row["negative_pct"] = ""
            if s.notna().any():
                row["min"] = ", ".join(sorted(s.dropna().unique()))[:60]
        rows.append(row)
    assert len(rows) == df.shape[1] and n == df.shape[0]
    return pd.DataFrame(rows)


def to_markdown_table(df: pd.DataFrame) -> str:
    """Minimal Markdown table writer (avoids an extra dependency)."""
    header = "| " + " | ".join(df.columns) + " |"
    rule = "|" + "|".join("---" for _ in df.columns) + "|"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, rule, *body])


def build_markdown(df: pd.DataFrame, prof: pd.DataFrame) -> str:
    groups = pd.Series(BUSINESS_GROUP).value_counts()
    table = prof[["column", "role", "value_chain", "meaning", "dtype", "complete_pct",
                  "min", "max", "negative_pct", "additivity"]]
    return "\n\n".join([
        "# Data Dictionary — corporate_income_statement.csv",
        "> Generated by `src/data_dictionary.py`. Do not edit by hand; re-run the script.",
        f"**Grain:** one row = one company × one fiscal quarter (`symbol`, `fiscalDateEnding`), "
        f"{df.shape[0]:,} rows × {df.shape[1]} columns, {df['symbol'].nunique()} companies.",
        "**Units:** whole units of `reportedCurrency` (to be confirmed in step 2.4). "
        "`min`/`max` are shown with thousands separators.",
        "## Columns",
        to_markdown_table(table),
        "## Additivity rules",
        "- **Flows** (every income-statement measure) can be summed over quarters (4 quarters = trailing twelve months) "
        "and across companies only when they report in the same currency.\n"
        "- **Ratios** (margins, growth, tax rate) are non-additive: always sum the components first, then divide.\n"
        "- **Semi-additive** measures (balances) do not occur in this dataset.",
        "## Hierarchies / drill paths",
        "- Company: `business group` → `symbol` (groups from `src/reference.py`)\n"
        "- Time: `fiscal year` → `fiscal quarter` → `fiscalDateEnding`; calendar alignment rule set in step 2.3",
        "## Business groups",
        to_markdown_table(groups.rename_axis("business_group").reset_index(name="companies")),
    ]) + "\n"


if __name__ == "__main__":
    df = load_raw()
    prof = profile(df)
    OUT_PATH.write_text(build_markdown(df, prof), encoding="utf-8", newline="\n")
    print(f"Columns by role : {prof['role'].value_counts().to_dict()}")
    empty = prof.loc[prof["complete_pct"] == 0, "column"].tolist()
    print(f"100% empty      : {len(empty)} -> {', '.join(empty)}")
    partial = prof.loc[(prof["complete_pct"] > 0) & (prof["complete_pct"] < 100), ["column", "complete_pct"]]
    print("Partly missing  : " + ", ".join(f"{c} {p}%" for c, p in partial.itertuples(index=False)))
    print(f"Written         : {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")