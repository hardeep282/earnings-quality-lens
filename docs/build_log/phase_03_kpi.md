# Build Log — Phase 03: North Star KPI
Project: Earnings Quality Lens · Milestone: M1 · Mode: GREENFIELD · Depth: STANDARD (skeleton)
Date(s): 2026-10-08 · Hours: 4 est / ⟨fill in⟩ actual · Status: Complete
Branch / PR: `phase-03-kpi` · Commit(s): ⟨fill from git log⟩ · Environment: Windows · PowerShell · VS Code · Python 3.12.3 · pandas 3.0.6 · duckdb 1.5.6

## 1. Objective
Fix one governed North Star KPI and its guardrail, with exact columns, edge-case rules, tests and a spec card. Serves US1 (ranking input), US3 (fair, recomputed ratios), US2 (forecast target in Phase 9); H1, H8.

## 2. What was covered
- Concepts: North Star + input metrics (Amplitude framework, adapted: our metric is lagging) · Goodhart's law → guardrail · TTM as a flow sum and its validity · growth on negative / near-zero bases · KPI tree identity 1 + g_OI = (1 + g_rev) × (m_t / m_t−4) and its additive log form · ratio of sums vs mean of ratios · field-level fitness for purpose · stale (carried-forward) values · known-answer, edge-case and golden-number tests · SQL RANGE windows over a quarter index · tie-out (reconciliation) between two implementations · KPI spec card
- Industry equivalents noted: dbt Semantic Layer (MetricFlow), Cube, LookML · Great Expectations / Soda "unchanged vs previous period" · pytest, dbt unit tests, snapshot tests · dbt docs / data catalogues (DataHub, Atlan, Collibra) · parallel-run reconciliation

## 3. What was built (artefacts)
| Artefact | Path | Purpose |
|---|---|---|
| Governed reference data | `src/reference.py` (+ `MANUAL_EXCLUSIONS`, `KPI_CAUTION`) | Steward exclusions with evidence; caution flags |
| North Star module | `src/kpis.py` | `input_validity` → `ttm_panel` → `north_star` → `like_for_like`; `build()` runs the chain |
| Tests | `tests/test_kpis.py` | 10 tests: known answer, missing quarter, stale rule, 5 status labels, ratio of sums, golden numbers |
| Spec card generator | `src/north_star_report.py` → `docs/03_north_star.md` | Spec card, D1–D7 effects, pandas/SQL/DAX/Excel versions, DuckDB tie-out, review lists |

## 4. Key results
- D1–D7 confirmed by owner [From my local run, identical to sandbox]
- Invalid inputs: 41 company-quarters (copied 4 · derived 19 · stale revenue 2 · stale OI 11 · missing 4 · manual 7)
- Coverage: 1,611 valid TTM of 1,753 calendar slots · 1,414 defined growth values · labels: turned profitable 28, loss narrowed 19, loss widened or flat 27 · base margin < 2%: 26 · no TTM pair: 239
- 2025Q3 like-for-like USD aggregate: +16.7% (n = 20, AVGO lags) vs naive mean 20.3%; margin 21.6% (+1.68 pp)
- Latest: PLTR +132.7% · LLY +75.0% · AVGO +72.9% (2025Q2) · TSM +55.4% · NVDA +55.0% with margin −3.87 pp · V margin −5.69 pp · TSLA −40.1%
- pandas ↔ SQL (DuckDB) tie-out: identical on 1,611 TTM and 1,414 growth values (max difference 0.0)
- Level breaks: 7 found, 6 already handled by D3/D7; TSLA 2012Q4 kept for Phase 6 review
- Tests: 18 passing (8 Phase 2 + 10 Phase 3)

## 5. Decisions made
| Decision | Options considered | Chosen | Why | Reversible? |
|---|---|---|---|---|
| D1 North Star | Revenue growth · net income growth · TTM operating-income growth | TTM operating-income growth | Isolates what management controls; TTM removes seasonality and fiscal-calendar effects | Yes |
| D2 TTM validity | Sum any 4 rows · 4 consecutive valid calendar quarters | Consecutive and valid | A gap or bad quarter would silently distort the total | Yes |
| D3 Input validity | Reuse row-level `exclude_from_modelling` · field-level | Field-level on revenue/OI | Fitness for purpose; keeps AMZN 2020Q4, BABA 2018, TSM 2018 whose KPI inputs are clean | Yes |
| Stale rule | Any exact repeat · repeat not confirmed by identity | Not confirmed by identity | Keeps genuine repeats (NVDA 2014-07, XOM 2025-03), flags TSM Q1 carry-forwards | Yes |
| D4 Awkward bases | Show % anyway · symmetric growth · labels | Labels; floor 2% base margin | Lowest COST/WMT base margin 2.46%, so thin-margin retailers are kept | Yes |
| D5 Guardrail | None · TTM margin + YoY pp | TTM margin + pp change + quadrant | Goodhart protection: growth bought with margin is visible | Yes |
| D6 Aggregate | Mean of growths · ratio of sums, like-for-like | Ratio of sums, coverage shown | 16.7% vs 20.3%: the mean is inflated by small fast growers | Yes |
| D7 Applicability | Exclude BRK-B · caution flag | Caution flag | Evidence is inferred; exclusion would hide data | Yes |
| SQL design | Calendar grid table · RANGE over q_idx | RANGE over q_idx + valid count | Handles gaps without building a grid | Yes |

## 6. Mistakes, errors and issues
**Issue 1 — Phase 2 copy check was row-level and missed single-column carry-forwards**
- **Type:** method gap (assistant, Phase 2) · **Root cause:** `repeated_quarters` required all four measures to repeat
- **Detected:** evidence scan before building the North Star (TSM Q1 `operatingIncome` = previous Q4 exactly, 10 times; AAPL 2006Q3 revenue stale)
- **Fix:** field-level stale check, confirmed by the row's accounting identity (`input_validity`) · **Prevention:** check every KPI input column individually for stale values; back-port to `quality_checks.py` in Phase 5 · **Impact:** none on delivered results (caught before KPI use)

**Issue 2 — First level-break labels marked BABA 2013Q1 as "kept"**
- **Type:** method design (caught in sandbox before delivery) · **Root cause:** the label ignored whether the *previous* quarter was excluded
- **Fix:** `prev_valid` check → "previous quarter excluded (D3)" · **Prevention:** label against both sides of a ratio · **Impact:** none for the user

**Issue 3 — ruff ISC004 on implicitly concatenated strings in the report**
- **Type:** code style (caught in sandbox) · **Root cause:** multi-line strings inside tuples without parentheses
- **Fix:** parenthesised every concatenated string · **Prevention:** run `ruff check` on each new file before delivery · **Impact:** none

**Issue 4 — Original Phase 0–2 chat deleted**
- **Type:** tooling / owner · **Root cause:** accidental deletion
- **Detected:** owner report · **Fix:** confirmed both published artifacts survive chat deletion (read and reopened); handoff file updated to 2026-10-08 · **Prevention:** download the build log `.md` to `C:\Projects\_handoffs\` after every phase · **Impact:** none

## 7. Debugging command sheet
| What the step is | Command | What it does |
|---|---|---|
| Show current branch | `git branch --show-current` | Confirms you are on `phase-03-kpi` |
| Branch explicitly from main | `git switch -c phase-03-kpi main` | Creates the phase branch from `main` |
| Exit a long Git listing | `q` | Leaves the pager when `:` or `(END)` appears |
| Run the North Star | `python -m src.kpis` | Prints validity, coverage, status, latest values, aggregate |
| Rebuild the spec card | `python -m src.north_star_report` | SQL tie-out + writes `docs/03_north_star.md` |
| Run tests | `python -m pytest -q` | 18 tests |

## 8. Validation performed
Every file run in the sandbox on a byte-identical CSV first; owner output identical at steps 3.2–3.4 (including 10,932 bytes for the generated card). Hand-calculated unit tests (+50%, +2.0 pp, ratio of sums 10%), KPI-tree identity test, golden-number regression test, and an independent SQL implementation reconciled to zero difference.

## 9. Changes to data and assumptions
No changes to raw data. New governed reference data: `MANUAL_EXCLUSIONS` (BABA 2011-06 → 2012-12, scale break) and `KPI_CAUTION` (BRK-B). New assumption: 2% base-margin floor [Assumed, evidence-based].

## 10. Deviations from plan
Added a field-level stale check and a level-break review list (not in the original plan) after the evidence scan. Added the SQL tie-out in Phase 3 instead of waiting for Phase 5.

## 11. Open issues and technical debt
Back-port field-level stale check to Phase 2 checks/scorecard (Phase 5) · BRK-B and TSLA 2012Q4 review (Phase 6) · DAX and Excel versions not executed (Phases 11 and 4) · ruff config for Phase 2 files (Phase 19).

## 12. Cost and resources
US$0.

## 13. Learning notes
A KPI is only as good as its edge-case rules. Most of the work was deciding what *not* to compute: loss bases, tiny bases, stale quarters. Two independent implementations agreeing is stronger evidence than any single test.

## 14. Career capture
- Transferable: TTM + like-for-like aggregation → Retail EPOS, Beverage (like-for-like sales), BA Airline (rolling RASK/CASK); field-level stale checks → any vendor feed; SQL RANGE windows → all SQL projects; spec card + tie-out → Banking AI (regulated metric definitions)
- CV bullet (draft): "Defined and governed a North Star KPI (TTM operating-income growth) with seven documented edge-case rules, hand-calculated and regression tests, and an independent SQL implementation that reconciled to zero difference across 1,414 values."
- Interview Q&A: *How do you handle growth on a loss base?* Status labels, not percentages. *Why not average growth rates?* 16.7% vs 20.3%: ratio of sums answers the business question. *How do you know SQL and Python agree?* Tie-out to zero difference. *What data issue surprised you?* TSM Q1 operating income carried forward 10 times, invisible to a row-level check.

## 15. Sources consulted
Amplitude *North Star Playbook* · Strathern (1997) *European Review* 5(3) 305–321 · Törnqvist, Vartia & Vartia (1985) *The American Statistician*, doi:10.1080/00031305.1985.10479385 · DAX Guide: DATESINPERIOD · DuckDB window-function documentation

## 16. Next steps
Phase 5 skeleton (M1): Bronze → Silver → Gold in DuckDB applying the cleaning plan and the North Star as a Gold KPI view, with row-count reconciliation; then baseline seasonal-naive forecast, Streamlit stub in Docker, deploy; Hiring Panel Review 1.