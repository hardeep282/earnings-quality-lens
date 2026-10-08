

"""Action-titled charts read from Gold (step S1.2). The title states the insight, computed from the data.

Uses matplotlib's object-oriented Figure (no pyplot), so the same function is safe inside the
Streamlit app (S1.3) and leaves no global figures behind.

Run from the project root:  python -m src.charts
"""
from __future__ import annotations

from pathlib import Path

import duckdb
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from src.baseline import LEVEL
from src.pipeline import DB_PATH

FIG_DIR = Path("docs/figures")
COLOURS = {"revenue": "#2a78d6", "operating_income": "#eb6834"}   # validated categorical slots 1-2
LABELS = {"revenue": "Revenue", "operating_income": "Operating income"}
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
TARGET_BAND = (0.75, 0.85)                                         # charter: 80% PI covers 75-85%


def load_coverage(db_path: Path = DB_PATH):
    """Company x measure coverage from gold.baseline_mase, wide, sorted so the worst sits at the top."""
    with duckdb.connect(str(db_path), read_only=True) as con:
        long = con.execute("SELECT symbol, measure, coverage FROM gold.baseline_mase").df()
    wide = long.pivot(index="symbol", columns="measure", values="coverage")
    return wide.sort_values("revenue", ascending=False)               # barh-style: last row plots on top


def coverage_chart(db_path: Path = DB_PATH) -> Figure:
    """Dot plot: share of actuals inside the baseline 80% interval, per company, revenue vs operating income."""
    cov = load_coverage(db_path)
    rev_mean, oi_mean = cov["revenue"].mean(), cov["operating_income"].mean()
    worst = cov["revenue"].idxmin()

    fig = Figure(figsize=(8, 9), dpi=150, facecolor=SURFACE)
    ax = fig.subplots()
    ax.set_facecolor(SURFACE)
    y = range(len(cov))
    ax.axvspan(*TARGET_BAND, color=GRID, zorder=0)
    ax.axvline(LEVEL, color=INK_2, linewidth=1, zorder=1)
    for i, symbol in enumerate(cov.index):                        # connector shows the gap per company
        ax.plot(cov.loc[symbol, ["revenue", "operating_income"]], [i, i], color=GRID, linewidth=2, zorder=2)
    for measure, colour in COLOURS.items():
        ax.scatter(cov[measure], y, s=64, color=colour, edgecolors=SURFACE, linewidths=2, zorder=3)

    ax.set_yticks(list(y), cov.index, color=INK, fontsize=9)
    ax.set_xlim(0, 1.02)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], ["0%", "20%", "40%", "60%", "80%", "100%"], color=INK_2)
    ax.set_xlabel("Share of actual quarters inside the baseline's 80% range", color=INK_2)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.annotate("target 75–85%", xy=(TARGET_BAND[1], len(cov) - 0.4), xytext=(4, 0),
                textcoords="offset points", fontsize=8, color=INK_2, va="center")

    handles = [Line2D([], [], marker="o", linestyle="", markersize=8, markerfacecolor=c,
                      markeredgecolor=SURFACE, label=LABELS[m]) for m, c in COLOURS.items()]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=9, labelcolor=INK)

    fig.suptitle(f"Same-quarter-last-year forecasts are overconfident: their 80% ranges caught\n"
                 f"actual revenue only {rev_mean:.0%} of the time ({worst} {cov.loc[worst, 'revenue']:.0%})",
                 x=0.03, ha="left", fontsize=12.5, fontweight="bold", color=INK)
    ax.set_title(f"Seasonal-naive baseline · 39 rolling origins from 2015Q4 · horizons 1–4 quarters\n"
                 f"Mean of companies: revenue {rev_mean:.1%}, operating income {oi_mean:.1%}",
                 loc="left", fontsize=8.5, color=INK_2, pad=10)
    fig.text(0.03, 0.01, "Source: corporate_income_statement.csv (SHA-256 0898c7c5…) → gold.baseline_mase. "
             "Portfolio project; fictional client; not investment advice.", fontsize=7, color=INK_2)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.87, bottom=0.08)
    return fig


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "s1_baseline_coverage.png"
    coverage_chart().savefig(out, facecolor=SURFACE)
    cov = load_coverage()
    print(f"Saved          : {out.as_posix()}")
    print(f"Companies      : {len(cov)}")
    print(f"Mean coverage  : revenue {cov['revenue'].mean():.1%}, operating income "
          f"{cov['operating_income'].mean():.1%} (target {TARGET_BAND[0]:.0%}-{TARGET_BAND[1]:.0%})")
    inside = ((cov >= TARGET_BAND[0]) & (cov <= TARGET_BAND[1])).sum()
    print(f"Inside target  : revenue {inside['revenue']} of 23, operating income {inside['operating_income']} of 23")
    print(f"Worst revenue  : {cov['revenue'].idxmin()} {cov['revenue'].min():.0%}")