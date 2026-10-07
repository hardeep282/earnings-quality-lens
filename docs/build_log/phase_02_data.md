

# Build Log — Phase 02: Data Understanding & Quality
Project: Earnings Quality Lens · Milestone: M1 · Mode: GREENFIELD · Depth: STANDARD
Date(s): 2026-10-07 · Hours: 5 est / ⟨fill in⟩ actual · Status: Complete
Branch / PR: `phase-02-data` · Commit(s): ⟨fill from git log⟩ · Environment: Windows · PowerShell · VS Code · Python 3.12.3 · pandas 3.0.6

## 1. Objective
Know exactly what one row means, how trustworthy each column is, and whether the data is fit to build on. Serves all user stories.

## 2. What was covered
- Concepts: grain · explicit missing-value tokens · float64 exactness (2^53) · semantic roles and additivity (Kimball) · accounting identities as internal accuracy checks · data generating process (vendor-derived and copied quarters) · MCAR / MAR / MNAR (Rubin 1976) · Cramér's V from chi-square · fiscal-to-calendar midpoint rule · DAMA UK six dimensions · readiness scoring
- Industry equivalents noted: DVC/lakeFS · Pandera/Great Expectations · dbt tests and docs · ydata-profiling/missingno · dbt source freshness · data catalogues

## 3. What was built (artefacts)
| Artefact | Path | Purpose |
|---|---|---|
| Loader with fingerprint guard | `src/data_load.py` | Single, typed, verified entry point to the raw data |
| Reference data | `src/reference.py` | Business groups, financials, non-US filers |
| Dictionary generator | `src/data_dictionary.py` → `docs/02_data_dictionary.md` | Role, additivity, completeness, range per column |
| Validity/consistency checks | `src/quality_checks.py` | Identities, negatives, copied quarters, derived values, currency |
| Context checks | `src/quality_context.py` | Missingness types, calendar rule, timeliness, opex mapping, tax rates, units |
| Report generator | `src/quality_report.py` → `docs/02_data_quality_report.md`, `data/interim/row_flags.csv` | Scorecard, readiness, cleaning plan, row flags |
| Tests | `tests/test_data_quality.py` | 8 tests: shape/grain, fingerprint guard, NA handling, calendar rule, Cramér's V |

## 4. Key results
- Readiness **96.7 / 100 → GO with documented exclusions** (Completeness 99.9 · Uniqueness 100 · Validity 100 · Consistency 87.9 · Timeliness 95.7 · Accuracy proxy 98.3) [From my local run]
- Identities: gross profit 94.6% (fails = financials) · operating income 89.8% (TSM 73, AMZN 57: vendor opex definitions) · EBITDA 99.5% · COGS duplicate 100% equal [From my local run]
- 28 vendor-derived rows (TSLA/PLTR pre-IPO, TSM to 2018, BABA 2018), 4 copied quarters → 29 rows excluded from modelling
- Missingness: R&D (V=0.75) and SG&A (V=0.86) depend on company; interest columns depend on time (V_year 0.91–0.97)
- Midpoint calendar rule: 0 collisions across 3 fiscal calendars; AVGO one quarter behind (2025Q2)
- Unmapped opex: PLTR 28.1%, AMZN 22.9%, ORCL 20.6%, BABA 18.5% of revenue → SG&A not comparable across companies
- Units: whole currency units (USD median $16.2bn per quarter)

## 5. Decisions made
| Decision | Options considered | Chosen | Why | Reversible? |
|---|---|---|---|---|
| Missing tokens | pandas defaults · explicit | Explicit (`None`, blank only) | Tickers like "NA" must survive | Yes |
| Operating income | Recompute · reported | Reported `operatingIncome` | Opex definitions differ by company | Yes |
| Missing R&D/SG&A | Fill 0 · not applicable | Not applicable | Missingness depends on company; 0 would invent data | Yes |
| Calendar alignment | Fiscal as-is · period-end month · midpoint | Midpoint (end − 45 days) | 0 collisions; economically correct | Yes |
| Derived/copied rows | Delete · keep and flag | Keep and flag; exclude from modelling | Context kept; models don't learn vendor arithmetic | Yes |
| Consistency metric | GP identity only · both identities | Both | GP-only (99%) hid a real issue | Yes |

## 6. Mistakes, errors and issues
**Issue 1 — Generated file differed in size on Windows (6,632 vs 6,570 bytes)**
- **Type:** assistant error · **Root cause:** `write_text` without `newline="\n"` writes CRLF on Windows
- **Detected:** comparing byte counts with the sandbox · **Fix:** `newline="\n"` on every generated file
- **Prevention:** always pin line endings for generated artefacts · **Impact:** none (5 min)

**Issue 2 — First missingness classifier mislabelled R&D as "scattered"**
- **Type:** method design (caught in sandbox before delivery) · **Root cause:** share-of-missing threshold rule ignored partial non-reporters
- **Fix:** replaced with Cramér's V against company and year; "too few to classify" below 10 gaps
- **Prevention:** use a statistic, not an ad-hoc threshold, when classifying patterns · **Impact:** none for the user

**Issue 3 — First scorecard flattered consistency (99%)**
- **Type:** method design (caught in sandbox) · **Root cause:** measured only the gross-profit identity
- **Fix:** consistency requires both identities (87.9%) · **Prevention:** test every metric against known failures · **Impact:** none for the user

## 7. Debugging command sheet
| What the step is | Command | What it does |
|---|---|---|
| Run any step module | `python -m src.<module>` | Runs from the project root so `src` imports and relative paths resolve |
| Re-generate the dictionary | `python -m src.data_dictionary` | Rewrites `docs/02_data_dictionary.md` |
| Preview Markdown in VS Code | `Ctrl + Shift + V` | Renders tables |
| Run tests | `python -m pytest -q` | Runs every test in `tests/` |

## 8. Validation performed
Every script was run in a sandbox on a byte-identical copy (same SHA-256) and the user's local output matched line for line at steps 2.1–2.5. 8 pytest tests pass.

## 9. Changes to data and assumptions
No changes to raw data. A2 (whole currency units) confirmed [Inferred from magnitude]. New rules recorded in the cleaning plan (applied in Phase 5).

## 10. Deviations from plan
Step 2.4 added an "unmapped opex" check not in the original plan, to resolve the Phase 1 AMZN flag.

## 11. Open issues and technical debt
ruff style warnings (implicit string concatenation) → configure in Phase 19 · Accuracy remains a proxy under the CSV-only rule.

## 12. Cost and resources
US$0.

## 13. Learning notes
A vendor dataset can contain rows the company never reported. Detecting them (non-round values, copied quarters) before modelling prevents models from learning the vendor's arithmetic.

## 14. Career capture
- Transferable: loader + fingerprint guard, generated dictionary, identity checks and scorecard → Beverage, Online Retail, Retail EPOS (any CSV source); Cramér's V missingness typing → Financial Resilience survey data; calendar mapping → BA Airline (fiscal years)
- CV bullet (draft): "Built a reproducible data-quality pipeline (fingerprinted loader, generated data dictionary, accounting-identity checks, DAMA six-dimension scorecard) that detected 29 vendor-derived or copied quarters and produced a 96.7/100 readiness score with a documented cleaning plan."
- Interview Q&A: *How did you validate data with no source of truth?* Internal identities + DGP checks, accuracy labelled as a proxy. *Why not fill missing R&D with 0?* Missingness depended on company (V=0.75). *How do you align fiscal calendars?* Midpoint rule, tested for collisions.

## 15. Sources consulted
pandas 3.0 release notes · Kimball Group dimensional modelling techniques (additivity) · Rubin (1976) Biometrika 63(3) · van Buuren, Flexible Imputation of Missing Data · UK Government Data Quality Framework (2020) / DAMA UK six dimensions

## 16. Next steps
Phase 3 — North Star KPI (branch `phase-03-kpi`), using the cleaning plan's KPI rules.