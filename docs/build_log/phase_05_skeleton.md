

# Build Log — Phase 05 (skeleton): Bronze → Silver → Gold in DuckDB
Project: Earnings Quality Lens · Milestone: M1 · Mode: GREENFIELD · Depth: STANDARD (skeleton)
Date(s): 2026-10-08 · Hours: 4 est / ⟨fill in⟩ actual · Status: Complete (skeleton; full Phase 5 in M2)
Branch / PR: `phase-05-skeleton` · Commit(s): ⟨fill from git log⟩ · Environment: Windows · PowerShell · VS Code · Python 3.12.3 · pandas 3.0.6 · duckdb 1.5.6

## 1. Objective
Turn the raw CSV into trusted, governed tables in one reproducible pipeline (Bronze → Silver → Gold), with row counts reconciled at every layer and the North Star served from SQL, proven equal to the tested Phase 3 Python.

## 2. What was covered
- Concepts: medallion architecture (Bronze raw / Silver validated / Gold business-ready) · raw layer kept as text · load log as lineage · strict CAST vs TRY_CAST · seeds as one source of truth for reference data · LAG windows · DuckDB list comprehensions · Kimball star schema (declared grain, surrogate keys, complete date dimension, fact vs dimension) · tables vs views · session-variable scope · reconciliation (row counts + row-by-row diff) · the four generic data tests (not_null, unique, accepted_values, relationships) · test isolation with temporary databases · regression and mutation testing
- Industry equivalents noted: dbt models/seeds/tests, Databricks medallion / Delta Live Tables, Airflow/Dagster orchestration, dbt Semantic Layer (MetricFlow), Datafold data-diff, Great Expectations / Soda, mutmut

## 3. What was built (artefacts)
| Artefact | Path | Purpose |
|---|---|---|
| Bronze SQL | `sql/pipeline/01_bronze.sql` | Raw CSV as text (1,750 × 27) + `bronze.load_log` (time, file, SHA-256, rows) |
| Silver SQL | `sql/pipeline/02_silver.sql` | Typed, snake_case, 5 empty + 1 duplicate column dropped, PLTR currency imputed and flagged, calendar quarter, Phase 2 row flags, Phase 3 D3 input flags (1,750 × 34) |
| Gold SQL | `sql/pipeline/03_gold.sql` | `dim_company` (23), `dim_quarter` (81), `fact_quarter` (1,750), views `north_star` (1,753) and `north_star_lfl` (74) |
| Pipeline runner | `src/pipeline.py` | Fingerprint check, seeds `ref.company`, `ref.manual_exclusion`, `ref.kpi_parameter`, runs SQL files in name order |
| Reconciliation | `src/reconcile.py` | Row counts CSV → Gold; Silver flags vs Phase 2/3 Python; Gold North Star vs Phase 3 Python |
| Data tests | `tests/test_pipeline.py` | 10 tests on an isolated temporary database |
| Runbook | `docs/RUNBOOK.md` | Rebuild the whole project from scratch, every command explained |

## 4. Key results
- Row counts: CSV = Bronze = Silver = Gold fact = 1,750 [From my local run, identical to sandbox]
- Silver vs Python: 11 checks × 1,750 rows, 0 differences (input_valid 1,709; derived rows 28; copied 4; stale OI 11)
- Gold vs Python: 1,753 slots, 1,611 TTM, 1,414 defined growth values, 74 LFL quarters, 0 differences
- 2025Q3 like-for-like USD (from SQL): +16.7% (n = 20), margin 21.6% (+1.68 pp)
- Tests: 28 passing (8 Phase 2 + 10 Phase 3 + 10 Phase 5)

## 5. Decisions made
| Decision | Options considered | Chosen | Why | Reversible? |
|---|---|---|---|---|
| Engine | PostgreSQL · cloud warehouse · DuckDB | DuckDB (single file) | 1,750 rows; no server to run; already pinned | Yes |
| Orchestration | dbt · Airflow · own runner | Own runner (SQL files in name order) | Every step visible; dbt decision revisited in Phase 5 full | Yes |
| Bronze typing | Infer types · all text | All text (`all_varchar`) | Nothing interpreted before Silver | Yes |
| Casting | TRY_CAST · CAST | CAST | Malformed numbers fail loudly instead of becoming NULL | Yes |
| Reference data | Hard-code in SQL · seed from `src/reference.py` | Seed `ref.*` tables | One source of truth for SQL and Python | Yes |
| KPI parameters | Session variables · parameter table | `ref.kpi_parameter` table | Views run in later sessions (incident P5.2) | Yes |
| Gold model | One wide table · star schema | Star schema, surrogate keys, complete quarter dimension | BI-ready, gaps visible, ticker changes isolated | Yes |
| North Star in Gold | Table · view | View | Always reflects the current fact table | Yes |
| Interest columns | Gold · Silver only | Silver only | Phase 2 rule: coverage depends on time | Yes |

## 6. Mistakes, errors and issues
**Issue P5.1 — Example command run literally (`my-new-branch` created)**
- **Type:** assistant explanation error · **Root cause:** a real-looking example inside an explanation of `git pull`
- **Detected:** owner output · **Fix:** `git switch main` → `git branch -d my-new-branch` → `git switch -c phase-05-skeleton main`
- **Prevention:** examples marked "example only, don't run" · **Impact:** none (empty branch, 2 min)

**Issue P5.2 — Gold view used a session variable; 26 rows silently mislabelled "defined"**
- **Type:** assistant design error (caught in sandbox by reconciliation before delivery) · **Root cause:** `SET VARIABLE` lives only for the session that sets it; a view is re-evaluated in later sessions where the variable is NULL, so `base_margin < NULL` never fired
- **Detected:** `gold_vs_python` showed 26 rows differing on `ns_growth` / `ns_status` · **Fix:** parameters stored in `ref.kpi_parameter`; regression test added
- **Prevention:** views read only tables; mutation check confirmed the test fails if the bug returns · **Impact:** none for the user

**Issue P5.3 — Assistant sandbox reset mid-phase**
- **Type:** tooling · **Root cause:** sandbox environment recycled
- **Fix:** rebuilt from the uploaded files and delivered code; re-verified against owner's Step 5.2 output before continuing · **Prevention:** keep every file delivered as copy-paste blocks; the repo is the source of truth · **Impact:** none

## 7. Debugging command sheet
| What the step is | Command | What it does |
|---|---|---|
| Delete an unwanted empty branch | `git branch -d my-new-branch` | Safe delete; refuses if the branch has unmerged work |
| Build the warehouse | `python -m src.pipeline` | Bronze → Silver → Gold into `data/processed/earnings.duckdb` |
| Prove SQL = Python | `python -m src.reconcile` | Row counts + Silver and Gold row-by-row diffs |
| Confirm the DB is not committed | `git check-ignore -v data\processed\earnings.duckdb` | Shows the `.gitignore` rule (`*.duckdb`) |
| Run all tests | `python -m pytest -q` | 28 tests |

## 8. Validation performed
Every file run in the sandbox on a byte-identical CSV first; owner output identical at 5.1–5.4. Row-count reconciliation across 4 layers; 22 row-by-row equality checks (11 Silver, 11 Gold) at 0 differences; 10 data tests; mutation check on the P5.2 regression test (bug reintroduced → 2 failures; restored → 28 pass).

## 9. Changes to data and assumptions
No changes to raw data. New governed table `ref.kpi_parameter` (identity_tolerance 0.01, min_base_margin 0.02). PLTR 2019 currency imputed as USD with `currency_imputed = true` (Phase 2 plan).

## 10. Deviations from plan
Added `ref.kpi_parameter` (not planned) after incident P5.2. Added `docs/RUNBOOK.md` at owner's request. Baseline forecast and the Docker stub move to the next M1 phase.

## 11. Open issues and technical debt
Back-port the field-level stale check into the Phase 2 scorecard · Phase 5 full (M2): advanced SQL library, EXPLAIN tuning, text-to-SQL, data contracts, monitoring, 10× scale test, dbt decision · ruff ISC004 in Phase 2 files (Phase 19).

## 12. Cost and resources
US$0.

## 13. Learning notes
A reconciliation that runs in a fresh session is stronger than one that runs inside the build: it caught a bug that only appears when someone else reads the view later.

## 14. Career capture
- Transferable: medallion pipeline with a load log → Beverage, Online Retail, Retail EPOS; star schema with complete date dimension → BA Airline (routes × months), Banking AI; SQL-vs-Python reconciliation → any migration; data tests → every SQL project
- CV bullet (draft): "Built a DuckDB medallion pipeline (Bronze → Silver → Kimball star schema) with a fingerprinted load log, reconciled row-by-row against tested Python across 1,750 company-quarters (22 checks, zero differences) and guarded by 28 automated data tests."
- Interview Q&A: *Why keep a raw layer?* Rebuild from it when cleaning logic changes. *What is the grain of your fact table?* Company × quarter, tested unique. *A bug you caught?* View relying on a session variable mislabelled 26 rows; moved parameters to a table and added a regression test proven by mutation.

## 15. Sources consulted
Databricks, *What is the medallion lakehouse architecture?* · Kimball Group, *Dimensional Modeling Techniques* · DuckDB documentation (`read_csv`, `SET VARIABLE`, window functions, `ANTI JOIN`, views) · dbt documentation, *data tests* · pytest documentation, fixtures and `tmp_path_factory`

## 16. Next steps
Rest of M1: baseline seasonal-naive forecast from Gold, Streamlit stub, Docker, deploy; Hiring Panel Review 1.