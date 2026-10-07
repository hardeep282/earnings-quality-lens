

"""Row-level validity and consistency checks on the raw data (Phase 2, step 2.3).

Run from the project root:  python -m src.quality_checks
"""
from __future__ import annotations

import pandas as pd

from src.data_load import KEY_COLS, load_raw
from src.reference import FINANCIALS

TOL = 0.01  # identities must hold within 1% of revenue

# name: (left side, right side as a function of the row) — each must hold for a clean row
IDENTITIES = {
    "gross_profit = revenue - cost_of_revenue":
        ("grossProfit", lambda d: d["totalRevenue"] - d["costOfRevenue"]),
    "operating_income = gross_profit - operating_expenses":
        ("operatingIncome", lambda d: d["grossProfit"] - d["operatingExpenses"]),
    "ebitda = ebit + d_and_a":
        ("ebitda", lambda d: d["ebit"] + d["depreciationAndAmortization"]),
    "cost_of_revenue = cogs_duplicate":
        ("costOfRevenue", lambda d: d["costofGoodsAndServicesSold"]),
}
MUST_BE_NON_NEGATIVE = ["totalRevenue", "costOfRevenue", "researchAndDevelopment",
                        "sellingGeneralAndAdministrative"]
MEASURES_FOR_REPEAT_CHECK = ["totalRevenue", "grossProfit", "operatingIncome", "netIncome"]


def identity_checks(df: pd.DataFrame) -> pd.DataFrame:
    """For each identity: share of testable rows where |left - right| <= 1% of revenue."""
    out = []
    for name, (left, right_fn) in IDENTITIES.items():
        gap = (df[left] - right_fn(df)).abs() / df["totalRevenue"].abs()
        testable = gap.notna()
        fails = testable & (gap > TOL)
        fin = df["symbol"].isin(FINANCIALS)
        out.append({
            "identity": name, "testable_rows": int(testable.sum()),
            "pass_pct": round(100 * (1 - fails.sum() / testable.sum()), 1),
            "fails_financials": int((fails & fin).sum()), "fails_other": int((fails & ~fin).sum()),
            "worst_companies": ", ".join(f"{k} {v}" for k, v in
                                         df.loc[fails, "symbol"].value_counts().head(4).items()),
        })
    return pd.DataFrame(out)


def negative_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where a quantity that cannot be negative is negative."""
    rows = []
    for col in MUST_BE_NON_NEGATIVE:
        bad = df[col] < 0
        rows.append({"column": col, "negative_rows": int(bad.sum()),
                     "companies": ", ".join(sorted(df.loc[bad, "symbol"].unique()))})
    return pd.DataFrame(rows)


def repeated_quarters(df: pd.DataFrame) -> pd.DataFrame:
    """Consecutive quarters of the same company with identical key measures (copied, not reported)."""
    d = df.sort_values(KEY_COLS)
    prev = d.groupby("symbol")[MEASURES_FOR_REPEAT_CHECK].shift(1)
    same = (d[MEASURES_FOR_REPEAT_CHECK] == prev).all(axis=1)
    return d.loc[same, ["symbol", "fiscalDateEnding"] + MEASURES_FOR_REPEAT_CHECK[:1]]


def not_whole_thousands(df: pd.DataFrame) -> pd.Series:
    """Rows where any measure is not a whole number of thousands.

    Companies report in thousands or millions, so a value like -142,426,500 suggests the
    quarter was derived by the vendor (e.g. an annual figure divided by 4), not reported.
    """
    measures = df.select_dtypes("number")
    return ((measures % 1000 != 0) & measures.notna()).any(axis=1)


def currency_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Each company should report in exactly one currency."""
    per_co = df.groupby("symbol")["reportedCurrency"].agg(
        currencies=lambda s: ", ".join(sorted(s.dropna().unique())),
        missing=lambda s: int(s.isna().sum()))
    return per_co[(per_co["currencies"].str.contains(",")) | (per_co["missing"] > 0)]


if __name__ == "__main__":
    pd.set_option("display.width", 160, "display.max_columns", 10, "display.max_colwidth", 50)
    df = load_raw()
    print("== Accounting identities (tolerance 1% of revenue) ==")
    print(identity_checks(df).to_string(index=False))
    print("\n== Values that should never be negative ==")
    print(negative_checks(df).to_string(index=False))
    rep = repeated_quarters(df)
    print(f"\n== Repeated quarters (identical to the previous quarter): {len(rep)} rows ==")
    print(rep.to_string(index=False))
    der = not_whole_thousands(df)
    print(f"\n== Rows with values not in whole thousands (possibly derived): {int(der.sum())} rows ==")
    print(df.loc[der].groupby("symbol")["fiscalDateEnding"].agg(["count", "min", "max"]).to_string())
    print("\n== Currency consistency issues ==")
    print(currency_consistency(df).to_string())