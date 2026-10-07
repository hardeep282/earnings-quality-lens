

"""North Star KPI: TTM operating-income growth with its margin guardrail (Phase 3, decisions D1-D7).

Run from the project root:  python -m src.kpis
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_load import KEY_COLS, load_raw
from src.quality_checks import TOL, repeated_quarters
from src.quality_context import calendar_quarter
from src.reference import KPI_CAUTION, MANUAL_EXCLUSIONS, NON_US

REV, OI = "totalRevenue", "operatingIncome"   # the only two inputs of the North Star
MIN_BASE_MARGIN = 0.02                         # D4: below this base margin, growth % is not meaningful


def input_validity(df: pd.DataFrame) -> pd.DataFrame:
    """D3: one row per company-quarter saying whether revenue and operating income can be trusted."""
    d = df.sort_values(KEY_COLS).reset_index(drop=True)
    out = d[KEY_COLS].copy()
    out["calendar_quarter"] = calendar_quarter(d["fiscalDateEnding"])

    rep = repeated_quarters(d)
    out["is_repeated"] = out.set_index(KEY_COLS).index.isin(rep.set_index(KEY_COLS).index)
    out["is_derived"] = ((d[[REV, OI]] % 1000 != 0) & d[[REV, OI]].notna()).any(axis=1)

    # A value identical to the previous quarter is stale unless the row's own identity confirms it
    rev_abs = d[REV].abs()
    gp_ties = (d["grossProfit"] - (d[REV] - d["costOfRevenue"])).abs() / rev_abs <= TOL
    oi_ties = (d[OI] - (d["grossProfit"] - d["operatingExpenses"])).abs() / rev_abs <= TOL
    for col, ties, name in [(REV, gp_ties, "stale_revenue"), (OI, oi_ties, "stale_oi")]:
        same = (d[col] == d.groupby("symbol")[col].shift(1)) & d[col].ne(0)
        out[name] = same & ~ties

    out["is_missing"] = d[[REV, OI]].isna().any(axis=1)
    out["is_manual"] = False
    for symbol, first, last, _reason in MANUAL_EXCLUSIONS:
        hit = (d["symbol"] == symbol) & d["fiscalDateEnding"].between(first, last)
        out.loc[hit, "is_manual"] = True

    flags = ["is_repeated", "is_derived", "stale_revenue", "stale_oi", "is_missing", "is_manual"]
    out["input_valid"] = ~out[flags].any(axis=1)
    out[REV], out[OI] = d[REV], d[OI]
    return out


def ttm_panel(valid: pd.DataFrame) -> pd.DataFrame:
    """D2: trailing-twelve-month sums on a complete calendar-quarter grid per company.

    Gaps in a company's history become empty rows, so a TTM needs 4 consecutive valid quarters.
    """
    frames = []
    for symbol, g in valid.groupby("symbol"):
        g = g.set_index("calendar_quarter")
        grid = pd.period_range(g.index.min(), g.index.max(), freq="Q")
        g = g.reindex(grid)
        ok = g["input_valid"].astype("boolean").fillna(False).astype(bool)
        t = pd.DataFrame({
            "symbol": symbol,
            "fiscalDateEnding": g["fiscalDateEnding"],
            "ttm_revenue": g[REV].where(ok).rolling(4, min_periods=4).sum(),
            "ttm_oi": g[OI].where(ok).rolling(4, min_periods=4).sum(),
        }, index=grid)
        t["base_ttm_revenue"] = t["ttm_revenue"].shift(4)   # same calendar quarter, one year earlier
        t["base_ttm_oi"] = t["ttm_oi"].shift(4)
        frames.append(t)
    return pd.concat(frames).rename_axis("calendar_quarter").reset_index()


def north_star(panel: pd.DataFrame) -> pd.DataFrame:
    """D1, D4, D5, D7: growth (or a status label), margin guardrail and caution flag."""
    p = panel.copy()
    p["ttm_margin"] = p["ttm_oi"] / p["ttm_revenue"]
    p["base_margin"] = p["base_ttm_oi"] / p["base_ttm_revenue"]
    p["margin_change_pp"] = 100 * (p["ttm_margin"] - p["base_margin"])

    pair = p["ttm_oi"].notna() & p["base_ttm_oi"].notna()
    base_le0 = pair & (p["base_ttm_oi"] <= 0)
    low_base = pair & ~base_le0 & (p["base_margin"] < MIN_BASE_MARGIN)
    defined = pair & ~base_le0 & ~low_base
    p["ns_status"] = np.select(
        [~pair,
         base_le0 & (p["ttm_oi"] > 0),
         base_le0 & (p["ttm_oi"] > p["base_ttm_oi"]),
         base_le0,
         low_base],
        ["no TTM pair", "turned profitable", "loss narrowed", "loss widened or flat",
         "base margin below 2%"],
        default="defined")
    p["ns_growth"] = (p["ttm_oi"] / p["base_ttm_oi"] - 1).where(defined)

    up_g, up_m = p["ns_growth"] > 0, p["margin_change_pp"] >= 0
    p["quality_quadrant"] = np.select(
        [defined & up_g & up_m, defined & up_g & ~up_m, defined & ~up_g & up_m, defined],
        ["growth with margin up", "growth with margin down", "decline with margin up",
         "decline with margin down"],
        default="")
    p["caution"] = p["symbol"].map(KPI_CAUTION).fillna("")
    return p


def like_for_like(ns: pd.DataFrame) -> pd.DataFrame:
    """D6: USD reporters with a TTM in both years, aggregated as a ratio of sums per calendar quarter."""
    both = ns[~ns["symbol"].isin(NON_US) & ns["ttm_oi"].notna() & ns["base_ttm_oi"].notna()]
    agg = both.groupby("calendar_quarter").agg(
        companies=("symbol", "size"),
        ttm_oi=("ttm_oi", "sum"), base_ttm_oi=("base_ttm_oi", "sum"),
        ttm_revenue=("ttm_revenue", "sum"), base_ttm_revenue=("base_ttm_revenue", "sum"))
    agg["ns_growth"] = (agg["ttm_oi"] / agg["base_ttm_oi"] - 1).where(agg["base_ttm_oi"] > 0)
    agg["ttm_margin"] = agg["ttm_oi"] / agg["ttm_revenue"]
    agg["margin_change_pp"] = 100 * (agg["ttm_margin"] - agg["base_ttm_oi"] / agg["base_ttm_revenue"])
    return agg.reset_index()


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the whole chain from the raw file: validity -> TTM -> North Star -> like-for-like."""
    valid = input_validity(load_raw())
    ns = north_star(ttm_panel(valid))
    return valid, ns, like_for_like(ns)


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    valid, ns, lfl = build()

    flags = ["is_repeated", "is_derived", "stale_revenue", "stale_oi", "is_missing", "is_manual"]
    print("== D3 Input validity ==")
    print(f"Company-quarters checked : {len(valid)}")
    print(f"Invalid inputs           : {int((~valid['input_valid']).sum())}  "
          + " · ".join(f"{f} {int(valid[f].sum())}" for f in flags))
    stale = valid[valid["stale_oi"] | valid["stale_revenue"]]
    print("Stale values             : " + ", ".join(
        f"{s} {d.date()}" for s, d in stale[["symbol", "fiscalDateEnding"]].itertuples(index=False)))

    print("\n== D2 TTM coverage ==")
    print(f"Calendar slots           : {len(ns)}  (rows + gap quarters)")
    print(f"Valid TTM values         : {int(ns['ttm_oi'].notna().sum())}")

    print("\n== D4 North Star status ==")
    print(ns["ns_status"].value_counts().to_string())

    print("\n== Latest North Star per company (calendar quarter) ==")
    latest = ns[ns["ttm_oi"].notna()].groupby("symbol").tail(1).sort_values("ns_growth")
    show = latest[["symbol", "calendar_quarter", "ns_growth", "ttm_margin", "margin_change_pp",
                   "quality_quadrant", "caution"]].copy()
    show["ns_growth"] = (100 * show["ns_growth"]).round(1)
    show["ttm_margin"] = (100 * show["ttm_margin"]).round(1)
    show["margin_change_pp"] = show["margin_change_pp"].round(2)
    show["caution"] = show["caution"].str[:30]
    print(show.rename(columns={"ns_growth": "growth_%", "ttm_margin": "margin_%"}).to_string(index=False))

    print("\n== D6 Like-for-like USD aggregate (last 4 calendar quarters) ==")
    tail = lfl.tail(4).copy()
    tail["ns_growth"] = (100 * tail["ns_growth"]).round(1)
    tail["ttm_margin"] = (100 * tail["ttm_margin"]).round(1)
    tail["margin_change_pp"] = tail["margin_change_pp"].round(2)
    print(tail[["calendar_quarter", "companies", "ns_growth", "ttm_margin", "margin_change_pp"]]
          .rename(columns={"ns_growth": "growth_%", "ttm_margin": "margin_%"}).to_string(index=False))