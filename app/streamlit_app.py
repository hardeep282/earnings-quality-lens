

"""Earnings Quality Lens: walking-skeleton app (step S1.3). Reads Gold only; computes nothing new.

Run from the project root (so `src` is importable):  python -m streamlit run app/streamlit_app.py
Prerequisite: python -m src.pipeline  then  python -m src.baseline
"""
from __future__ import annotations

import threading

import duckdb
import pandas as pd
import streamlit as st

from src.baseline import FIRST_ORIGIN, LEVEL
from src.charts import coverage_chart
from src.pipeline import DB_PATH

st.set_page_config(page_title="Earnings Quality Lens", layout="wide")
_PLOT_LOCK = threading.RLock()          # matplotlib is not thread-safe; Streamlit serves users on threads


@st.cache_data
def query(sql: str) -> pd.DataFrame:
    """Read-only query against Gold. Cached: the data only changes when the pipeline is rebuilt."""
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(sql).df()


def gold_ready() -> bool:
    """True if the warehouse exists and the S1.1 baseline tables have been written."""
    if not DB_PATH.exists():
        return False
    found = query("SELECT count(*) AS n FROM information_schema.tables WHERE table_schema = 'gold' "
                  "AND table_name IN ('north_star', 'north_star_lfl', 'baseline_forecast', 'baseline_mase')")
    return int(found["n"].iloc[0]) == 4


st.title("Earnings Quality Lens")
st.caption("Quarterly growth-quality scoring and forecasting for 23 global mega-caps, 2005–2025")
st.warning("Portfolio project. **Alpha Capital Partners is a fictional client. Not investment advice.** "
           "Every number is computed from one supplied CSV of reported income statements; nothing is fetched "
           "from the internet and no figure comes from a language model.")

if not gold_ready():
    st.error("The Gold tables are missing. From the project root, run:")
    st.code("python -m src.pipeline\npython -m src.baseline", language="powershell")
    st.stop()

lfl = query("SELECT * FROM gold.north_star_lfl ORDER BY calendar_quarter DESC LIMIT 1").iloc[0]
mase = query("SELECT measure, avg(mase) AS mase, avg(coverage) AS coverage "
             "FROM gold.baseline_mase GROUP BY measure").set_index("measure")

# ---- Headline: the North Star, like-for-like USD -------------------------------------------------
st.subheader(f"North Star, {lfl['calendar_quarter']}: TTM operating income growth")
c1, c2, c3 = st.columns(3)
c1.metric("TTM operating income growth (USD, like-for-like)", f"{lfl['ns_growth']:+.1%}",
          help=f"Ratio of sums over {lfl['companies']} US-dollar reporters with a TTM value in both years.")
c2.metric("TTM operating margin", f"{lfl['ttm_margin']:.1%}", delta=f"{lfl['margin_change_pp']:+.2f} pp YoY",
          help="Guardrail: growth bought with falling margins is lower quality.")
rev_cov = mase.loc["revenue", "coverage"]
c3.metric("Baseline 80% range coverage (revenue)", f"{rev_cov:.1%}",
          delta=f"{100 * (rev_cov - LEVEL):+.1f} pp vs 80% target",
          help="Share of backtest quarters whose actual revenue fell inside the seasonal-naive 80% range.")

# ---- North Star by company -----------------------------------------------------------------------
st.subheader("Latest quarter by company")
latest = query("""
    SELECT symbol, calendar_quarter, ns_growth, ns_status, ttm_margin, margin_change_pp,
           quality_quadrant, caution
    FROM gold.north_star
    QUALIFY quarter_key = max(quarter_key) OVER (PARTITION BY symbol)
    ORDER BY ns_growth DESC NULLS LAST
""")
st.dataframe(latest, hide_index=True, column_config={
    "symbol": "Company", "calendar_quarter": "Quarter",
    "ns_growth": st.column_config.NumberColumn("TTM OI growth", format="percent"),
    "ns_status": "Status",
    "ttm_margin": st.column_config.NumberColumn("TTM margin", format="percent"),
    "margin_change_pp": st.column_config.NumberColumn("Margin change", format="%+.2f pp"),
    "quality_quadrant": "Quality quadrant", "caution": "Caution"})
st.caption("Growth is a % only when the base year is profitable with a margin of at least 2%; otherwise a "
           "label is shown (definition D1–D7 in docs/03_north_star.md). Ratios are within each company, "
           "in its reported currency.")

# ---- Baseline forecast ---------------------------------------------------------------------------
st.subheader("Baseline forecast: same quarter last year")
st.markdown(f"Backtest from {FIRST_ORIGIN}, 1–4 quarters ahead. Mean MASE across companies: "
            f"revenue **{mase.loc['revenue', 'mase']:.2f}**, operating income "
            f"**{mase.loc['operating_income', 'mase']:.2f}**. Later models must be at least 10% lower.")
left, right = st.columns([3, 2], gap="large")
with left, _PLOT_LOCK:
    st.pyplot(coverage_chart(DB_PATH))

fc = query("SELECT * FROM gold.baseline_forecast")
companies = sorted(fc["symbol"].unique())
with right:
    symbol = st.selectbox("Company", companies, index=companies.index("NVDA"))
    one = fc[fc["symbol"] == symbol].pivot(index="target_quarter", columns="measure",
                                           values=["forecast", "lo80", "hi80"])
    table = pd.DataFrame({
        "Revenue": one[("forecast", "revenue")] / 1e9,
        "80% low": one[("lo80", "revenue")] / 1e9,
        "80% high": one[("hi80", "revenue")] / 1e9,
        "Op. income": one[("forecast", "operating_income")] / 1e9,
        "Margin": one[("forecast", "operating_income")] / one[("forecast", "revenue")],
    }).rename_axis("Quarter")
    currency = fc.loc[fc["symbol"] == symbol, "currency"].iloc[0]
    st.markdown(f"**{symbol}: next four quarters** ({currency} bn; margin = operating income ÷ revenue)")
    st.dataframe(table, column_config={
        **{c: st.column_config.NumberColumn(format="%.2f") for c in table.columns[:4]},
        "Margin": st.column_config.NumberColumn(format="percent")})
    st.caption("Seasonal-naive: each forecast equals the same quarter one year earlier. The 80% range uses "
               "the spread of past year-on-year changes and is known to be too narrow (see chart). A "
               "calibrated model replaces it in Phase 9.")
    