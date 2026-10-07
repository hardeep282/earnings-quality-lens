# Changelog
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow milestones.

## [Unreleased]
### Added
- Phase 3: North Star KPI in `src/kpis.py` (field-level input validity incl. stale-value check, TTM on a calendar grid, TTM operating-income growth with status labels, margin guardrail and quality quadrant, like-for-like USD aggregate); governed `MANUAL_EXCLUSIONS` and `KPI_CAUTION` in `src/reference.py`; spec card generator with DuckDB SQL tie-out (`src/north_star_report.py` → `docs/03_north_star.md`); 10 new tests (18 total).
- Phase 2 (backfilled 2026-10-08): typed loader with SHA-256 guard, generated data dictionary, accounting-identity and data-generating-process checks, DAMA six-dimension scorecard (readiness 96.7), row flags, 8 tests.
- Phase 1 (backfilled 2026-10-08): business understanding, issue tree, pre-registered hypotheses H1–H9.
- Phase 0: project charter, tool decision register (v0.2, CSV-only constraint), Build Log entries 00A and 00B, master Build Log index.

## [0.0.1] — 2026-10-06
### Added
- Repository skeleton, pinned Python 3.12 environment, `.gitignore`, `.gitattributes`, `.env.example`, README, raw dataset with SHA-256 fingerprint.