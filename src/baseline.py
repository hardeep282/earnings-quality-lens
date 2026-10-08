

"""Seasonal-naive baseline: next-4-quarter forecasts, rolling-origin backtest and MASE (step S1.1).

Every later forecasting model (Phase 9) is scored on the SAME origins, horizons and metric,
and must beat this baseline by >= 10% MASE (charter success criterion).

Run from the project root:  python -m src.baseline
"""
from __future__ import annotations

from pathlib import Path
from statistics import NormalDist

import duckdb
import numpy as np
import pandas as pd

from src.pipeline import DB_PATH

SEASON = 4                 # m: quarters per year
HORIZON = 4                # h = 1..4: the next four quarters (user story US2)
FIRST_ORIGIN = "2015Q4"    # first backtest origin, shared with every later model
MIN_SCALE_PAIRS = 12       # an origin is scored only after 3 years of valid seasonal differences
LEVEL = 0.80               # prediction-interval level
Z = NormalDist().inv_cdf(0.5 + LEVEL / 2)   # 1.2816 for 80%
MEASURES = {"revenue": "total_revenue", "operating_income": "operating_income"}


def quarter_key(label: str) -> int:
    """'2015Q4' -> 8064, the same integer key as gold.dim_quarter (year * 4 + quarter)."""
    return int(label[:4]) * 4 + int(label[-1])


def load_series(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Long table (symbol, measure, quarter_key, value) on a complete calendar grid per company.

    A value is usable only if the row passed the North Star input check (input_valid) and is not
    flagged exclude_from_modelling (Phase 2). Unusable values and calendar gaps become NaN.
    """
    query = """
        SELECT d.symbol, d.reported_currency, f.quarter_key, f.total_revenue, f.operating_income,
               f.input_valid AND NOT f.exclude_from_modelling AS usable
        FROM gold.fact_quarter AS f JOIN gold.dim_company AS d USING (company_key)
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        raw = con.execute(query).df()
    frames = []
    for symbol, g in raw.groupby("symbol"):
        currency = g["reported_currency"].iloc[0]
        grid = pd.RangeIndex(g["quarter_key"].min(), g["quarter_key"].max() + 1, name="quarter_key")
        g = g.set_index("quarter_key").reindex(grid)          # calendar gaps appear as NaN rows
        usable = g["usable"].eq(True)                         # NaN (gap) counts as not usable
        for measure, column in MEASURES.items():
            frames.append(pd.DataFrame({"symbol": symbol, "currency": currency, "measure": measure,
                                        "quarter_key": grid,
                                        "value": g[column].where(usable).to_numpy(dtype=float)}))
    return pd.concat(frames, ignore_index=True)


def seasonal_naive(y: pd.Series, origin: int, horizon: int = HORIZON, m: int = SEASON) -> np.ndarray:
    """y_hat(T+h | T) = y(T + h - m(k + 1)), k = (h - 1) // m. y is indexed by consecutive quarter keys."""
    keys = [origin + h - m * ((h - 1) // m + 1) for h in range(1, horizon + 1)]
    return y.reindex(keys).to_numpy(dtype=float)


def scale_stats(y: pd.Series, origin: int, m: int = SEASON) -> tuple[float, float, int]:
    """In-sample seasonal-naive residuals up to the origin: (MAE = MASE scale, RMS = sigma, pairs used).

    Only data at or before the origin is used, so the scale never sees the future.
    """
    train = y.loc[:origin]
    resid = (train - train.shift(m)).dropna()
    if resid.empty:
        return np.nan, np.nan, 0
    return float(resid.abs().mean()), float(np.sqrt((resid ** 2).mean())), int(resid.size)


def backtest(series: pd.DataFrame, first_origin: str = FIRST_ORIGIN) -> pd.DataFrame:
    """Rolling (expanding-window) origin evaluation: one row per company x measure x origin x horizon."""
    rows = []
    start = quarter_key(first_origin)
    for (symbol, measure), g in series.groupby(["symbol", "measure"]):
        y = g.set_index("quarter_key")["value"]
        last = int(y.index.max())
        for origin in range(max(start, int(y.index.min())), last):
            scale, sigma, pairs = scale_stats(y, origin)
            if pairs < MIN_SCALE_PAIRS or not scale > 0:
                continue
            forecast = seasonal_naive(y, origin)
            for h in range(1, HORIZON + 1):
                target = origin + h
                if target > last:
                    break
                actual = y.loc[target]
                if np.isnan(actual) or np.isnan(forecast[h - 1]):
                    continue
                half = Z * sigma * np.sqrt((h - 1) // SEASON + 1)
                rows.append((symbol, measure, origin, h, target, actual, forecast[h - 1],
                             abs(actual - forecast[h - 1]) / scale,
                             forecast[h - 1] - half <= actual <= forecast[h - 1] + half))
    return pd.DataFrame(rows, columns=["symbol", "measure", "origin", "h", "target", "actual",
                                       "forecast", "scaled_abs_error", "covered"])


def mase_table(bt: pd.DataFrame) -> pd.DataFrame:
    """Per company x measure: MASE (mean scaled absolute error), scored forecasts, 80% PI coverage."""
    out = (bt.groupby(["symbol", "measure"])
             .agg(mase=("scaled_abs_error", "mean"), n=("scaled_abs_error", "size"),
                  coverage=("covered", "mean"))
             .reset_index())
    return out


def overall(mase: pd.DataFrame) -> pd.DataFrame:
    """Headline per measure: mean of company MASEs (primary, each company weighted equally) and median."""
    return (mase.groupby("measure")
                .agg(companies=("mase", "size"), mase_mean=("mase", "mean"),
                     mase_median=("mase", "median"), coverage=("coverage", "mean"))
                .reset_index())


def forecast_next(series: pd.DataFrame) -> pd.DataFrame:
    """Next four quarters per company from its latest quarter, with 80% normal intervals (fpp3 Table 5.2)."""
    rows = []
    for (symbol, measure), g in series.groupby(["symbol", "measure"]):
        y = g.set_index("quarter_key")["value"]
        origin = int(y.index.max())
        _, sigma, _ = scale_stats(y, origin)
        for h, point in enumerate(seasonal_naive(y, origin), start=1):
            half = Z * sigma * np.sqrt((h - 1) // SEASON + 1)
            rows.append((symbol, g["currency"].iloc[0], measure, origin, origin + h, h,
                         point, point - half, point + half))
    fc = pd.DataFrame(rows, columns=["symbol", "currency", "measure", "origin_key", "target_key", "h",
                                     "forecast", "lo80", "hi80"])
    fc["target_quarter"] = [f"{(k - 1) // 4}Q{(k - 1) % 4 + 1}" for k in fc["target_key"]]
    return fc


def write_gold(fc: pd.DataFrame, mase: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    """Persist results next to the star schema so the app and later phases read one place."""
    with duckdb.connect(str(db_path)) as con:
        for name, frame in [("baseline_forecast", fc), ("baseline_mase", mase)]:
            con.register("out_df", frame)
            con.execute(f"CREATE OR REPLACE TABLE gold.{name} AS SELECT * FROM out_df")
            con.unregister("out_df")


if __name__ == "__main__":
    series = load_series()
    bt = backtest(series)
    mase = mase_table(bt)
    head = overall(mase)
    fc = forecast_next(series)
    write_gold(fc, mase)

    usable = series["value"].notna().sum()
    print(f"Series         : {series[['symbol', 'measure']].drop_duplicates().shape[0]} "
          f"(23 companies x 2 measures), {usable} usable values of {len(series)} grid slots")
    print(f"Backtest       : origins {FIRST_ORIGIN} onward, h = 1..{HORIZON}, "
          f"{len(bt)} scored forecasts, {bt['origin'].nunique()} distinct origins")
    print(f"Interval       : {LEVEL:.0%} normal, z = {Z:.4f}\n")

    wide = mase.pivot(index="symbol", columns="measure", values=["mase", "coverage"]).round(2)
    wide.columns = [f"{a}_{'oi' if b == 'operating_income' else 'rev'}" for a, b in wide.columns]
    print("== MASE and 80% interval coverage by company ==")
    print(wide[["mase_rev", "mase_oi", "coverage_rev", "coverage_oi"]].to_string())

    print("\n== Overall (mean of company MASEs = the number later models must beat by >= 10%) ==")
    print(head.round(3).to_string(index=False))

    by_h = bt.groupby(["measure", "h"])["scaled_abs_error"].mean().unstack().round(3)
    print("\n== MASE by horizon (all scored forecasts) ==")
    print(by_h.to_string())

    nvda = fc[(fc["symbol"] == "NVDA") & (fc["measure"] == "revenue")]
    print("\n== Example: NVDA revenue, next 4 quarters (USD bn) ==")
    print((nvda.set_index("target_quarter")[["forecast", "lo80", "hi80"]] / 1e9).round(2).to_string())
    print(f"\nWritten        : gold.baseline_forecast ({len(fc)} rows), gold.baseline_mase ({len(mase)} rows)")