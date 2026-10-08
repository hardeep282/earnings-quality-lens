



# Earnings Quality Lens

Quarterly growth-quality scoring and forecasting for 23 global mega-caps (2005–2025), built end to end: data pipeline → statistics → forecasting → dashboard → AI analyst → AWS deployment.

> **Status:** > **Status:** Phases 0–3 and the Phase 5 skeleton complete — data quality audited (96.7/100), North Star KPI defined and tested, and a DuckDB Bronze → Silver → Gold warehouse reconciled to the tested Python (0 differences, 28 tests). Rebuild steps: [docs/RUNBOOK.md](docs/RUNBOOK.md). Next: baseline forecast and deployed app (milestone M1).
> **Not investment advice.** Portfolio project; the client "Alpha Capital Partners" is fictional.

## Data
- **File:** `data/raw/corporate_income_statement.csv` — 1,750 company-quarters × 27 columns, 23 companies, fiscal quarters 2005-08 → 2025-10
- **Label:** real public-company figures (course-supplied extract in Alpha Vantage `INCOME_STATEMENT` format)
- **SHA-256:** `0898C7C5095A153B3D829ECFD788533722417A706A7F31ADB23121842561DA30`
- **Constraint:** this CSV is the only data source; nothing is fetched from the internet.

## Project structure
| Folder | Purpose |
|---|---|
| `data/raw` → `data/interim` → `data/processed` | Bronze → Silver → Gold |
| `sql/` | Medallion SQL and query library |
| `src/` | Reusable Python (KPIs, features, models) |
| `notebooks/` | EDA and statistics |
| `app/` | Streamlit UI + FastAPI service |
| `agents/`, `rag/`, `evals/` | AI analyst layer and its evaluations |
| `docs/` | Charter, decision register, Build Log |

## Setup (Windows)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```