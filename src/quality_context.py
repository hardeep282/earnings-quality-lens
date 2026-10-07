



"""Missingness types, calendar alignment, timeliness and the Phase 1 flags (Phase 2, step 2.4).

Run from the project root:  python -m src.quality_context
"""
from __future__ import annotations

import pandas as pd

from src.data_load import load_raw

NEVER_REPORTS = 0.9   # a company "never reports" a column if >= 90% of its rows are missing
STRONG = 0.5          # Cramer's V at or above this = missingness strongly tied to that variable
MIN_MISSING = 10      # fewer missing cells than this are too few to classify


def cramers_v(flag: pd.Series, groups: pd.Series) -> float:
    """Association between a yes/no flag and a category (0 = none, 1 = perfect).

    Built from the chi-square statistic of the 2 x k contingency table: V = sqrt(chi2 / n).
    """
    table = pd.crosstab(flag, groups)
    if table.shape[0] < 2:
        return 0.0
    expected = table.sum(axis=1).to_numpy()[:, None] * table.sum(axis=0).to_numpy()[None, :] / table.to_numpy().sum()
    chi2 = ((table.to_numpy() - expected) ** 2 / expected).sum()
    return float((chi2 / table.to_numpy().sum()) ** 0.5)


def missingness_types(df: pd.DataFrame) -> pd.DataFrame:
    """Classify each partly-missing column by what its gaps depend on: company, time, or nothing."""
    out = []
    year = df["fiscalDateEnding"].dt.year
    for col in df.columns[3:]:
        miss = df[col].isna()
        if miss.sum() == 0 or miss.all():
            continue
        v_company = cramers_v(miss, df["symbol"])
        v_year = cramers_v(miss, year)
        rate_by_co = miss.groupby(df["symbol"]).mean()
        never = rate_by_co[rate_by_co >= NEVER_REPORTS].index
        if miss.sum() < MIN_MISSING:
            kind = "Too few to classify"
        elif v_company >= STRONG and v_company >= v_year:
            kind = "Depends on company (MAR given company)"
        elif v_year >= STRONG:
            kind = "Depends on time (MAR given time)"
        else:
            kind = "No strong pattern (MCAR plausible)"
        out.append({"column": col, "missing_rows": int(miss.sum()),
                    "V_company": round(v_company, 2), "V_year": round(v_year, 2),
                    "never_reported_by": ", ".join(sorted(never))[:40], "type": kind})
    return pd.DataFrame(out)


def calendar_quarter(dates: pd.Series) -> pd.Series:
    """Midpoint rule: a fiscal quarter belongs to the calendar quarter containing its midpoint.

    The midpoint is ~45 days before the period end, so a quarter ending 31 Jan
    (Nov-Jan) maps to Q4 of the previous year, and one ending 28 Feb (Dec-Feb) to Q1.
    """
    return (dates - pd.Timedelta(days=45)).dt.to_period("Q")


def calendar_check(df: pd.DataFrame) -> pd.DataFrame:
    d = df[["symbol", "fiscalDateEnding"]].copy()
    d["cal_q"] = calendar_quarter(d["fiscalDateEnding"])
    d["end_month"] = d["fiscalDateEnding"].dt.month
    patterns = d.groupby("symbol")["end_month"].agg(lambda s: "/".join(map(str, sorted(s.unique()))))
    collisions = int(d.duplicated(["symbol", "cal_q"]).sum())
    span = d.groupby("symbol")["cal_q"].agg(["min", "max", "count"])
    span["expected"] = span.apply(lambda r: (r["max"] - r["min"]).n + 1, axis=1)
    span["missing_quarters"] = span["expected"] - span["count"]
    span["fiscal_end_months"] = patterns
    print(f"Calendar-quarter collisions (two fiscal quarters -> same calendar quarter): {collisions}")
    return span[["fiscal_end_months", "min", "max", "count", "missing_quarters"]]


def timeliness(df: pd.DataFrame) -> pd.Series:
    """Latest quarter per company, as calendar quarter."""
    return calendar_quarter(df.groupby("symbol")["fiscalDateEnding"].max()).value_counts().sort_index()


def unmapped_opex(df: pd.DataFrame) -> pd.DataFrame:
    """Operating expenses not explained by R&D + SG&A, as % of revenue (last 8 quarters)."""
    recent = df.sort_values("fiscalDateEnding").groupby("symbol").tail(8)
    s = recent.groupby("symbol")[["totalRevenue", "operatingExpenses", "researchAndDevelopment",
                                  "sellingGeneralAndAdministrative"]].sum(min_count=1)
    s = s.fillna({"researchAndDevelopment": 0})
    out = pd.DataFrame({
        "sga_pct_rev": 100 * s["sellingGeneralAndAdministrative"] / s["totalRevenue"],
        "unmapped_opex_pct_rev": 100 * (s["operatingExpenses"] - s["researchAndDevelopment"]
                                        - s["sellingGeneralAndAdministrative"]) / s["totalRevenue"],
    }).round(1)
    return out.sort_values("unmapped_opex_pct_rev", ascending=False).head(6)


def tax_rate_check(df: pd.DataFrame) -> pd.DataFrame:
    """Trailing-4-quarter effective tax rate; flags rates outside 0-40%."""
    last4 = df.sort_values("fiscalDateEnding").groupby("symbol").tail(4)
    s = last4.groupby("symbol")[["incomeTaxExpense", "incomeBeforeTax"]].sum()
    etr = (100 * s["incomeTaxExpense"] / s["incomeBeforeTax"]).round(1)
    loss_quarters = int((df["incomeBeforeTax"] <= 0).sum())
    print(f"Quarters with pre-tax loss (tax rate undefined): {loss_quarters}")
    return etr[(etr < 5) | (etr > 40)].rename("ttm_etr_pct").to_frame()


def units_check(df: pd.DataFrame) -> pd.Series:
    """Median quarterly revenue per currency, in billions: tells us the unit of the figures."""
    return (df.groupby("reportedCurrency")["totalRevenue"].median() / 1e9).round(1)


if __name__ == "__main__":
    pd.set_option("display.width", 170, "display.max_colwidth", 70)
    df = load_raw()
    print("== Missingness types ==")
    print(missingness_types(df).to_string(index=False))
    print("\n== Calendar alignment (midpoint rule) ==")
    print(calendar_check(df).to_string())
    print("\n== Timeliness: latest calendar quarter per company ==")
    print(timeliness(df).to_string())
    print("\n== Phase 1 flag: operating expenses not explained by R&D + SG&A (top 6, last 8 quarters) ==")
    print(unmapped_opex(df).to_string())
    print("\n== Phase 1 flag: effective tax rates below 5% or outside 0-40% (last 4 quarters) ==")
    print(tax_rate_check(df).to_string())
    print("\n== Units: median quarterly revenue by currency (billions) ==")
    print(units_check(df).to_string())