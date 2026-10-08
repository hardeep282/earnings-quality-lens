

# Runbook — Earnings Quality Lens

How to rebuild this whole project from scratch on Windows, and what the outputs should be.
Every command runs in **PowerShell from the project root** (`C:\Projects\earnings-quality-lens`).
Updated at the end of every phase. Last update: Phase 5 skeleton (2026-10-08).

> Not investment advice. Portfolio project; the client "Alpha Capital Partners" is fictional.

## 1. Prerequisites
| Tool | Version | Check |
|---|---|---|
| Python | 3.12 | `py -3.12 --version` |
| Git | 2.42+ | `git --version` |
| VS Code | any recent | Python extension, interpreter set to `.venv` |

## 2. Get the code
```powershell
cd C:\Projects
git clone https://github.com/hardeep282/earnings-quality-lens.git
cd earnings-quality-lens
git switch main
git log --oneline -3
```
| Command | What it does |
|---|---|
| `git clone ...` | Downloads the repository into a new folder |
| `cd earnings-quality-lens` | Moves into the project root; every later command runs from here |
| `git switch main` | Makes sure you're on the finished, merged work |
| `git log --oneline -3` | Shows the latest commits as a sanity check |

## 3. Environment
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
| Command | What it does |
|---|---|
| `py -3.12 -m venv .venv` | Creates an isolated Python environment in `.venv` |
| `.\.venv\Scripts\Activate.ps1` | Activates it; the prompt starts with `(.venv)` |
| `pip install -r requirements.txt` | Installs the pinned versions (pandas 3.0.6, duckdb 1.5.6, …) |
| `Copy-Item .env.example .env` | Creates your local settings file (paths; API key added in Phase 12) |

## 4. Verify the data
```powershell
python -m src.data_load
```
| Command | What it does |
|---|---|
| `python -m src.data_load` | Checks the CSV's SHA-256 fingerprint and prints its shape. Stops with "Fingerprint mismatch" if the file changed |

## 5. Rebuild the documents (Phases 2–3)
```powershell
python -m src.data_dictionary
python -m src.quality_report
python -m src.kpis
python -m src.north_star_report
```
| Command | Produces |
|---|---|
| `python -m src.data_dictionary` | `docs/02_data_dictionary.md` |
| `python -m src.quality_report` | `docs/02_data_quality_report.md` + `data/interim/row_flags.csv` |
| `python -m src.kpis` | North Star summary in the terminal |
| `python -m src.north_star_report` | `docs/03_north_star.md` (spec card + SQL tie-out) |

## 6. Build the warehouse (Phase 5)
```powershell
python -m src.pipeline
python -m src.reconcile
```
| Command | What it does |
|---|---|
| `python -m src.pipeline` | Bronze → Silver → Gold into `data/processed/earnings.duckdb` (git-ignored, rebuildable) |
| `python -m src.reconcile` | Proves every layer: row counts, Silver flags = Python, Gold North Star = Python |

## 7. Run the tests
```powershell
python -m pytest -q
```
Expected: `28 passed`.

## 8. Expected numbers (if yours match, the rebuild worked)
| Check | Expected |
|---|---|
| CSV SHA-256 | starts `0898c7c5`, ends `61da30` |
| Rows × columns | 1,750 × 27; 23 companies |
| Readiness score | 96.7 / 100 (GO with documented exclusions) |
| Excluded from modelling | 29 rows |
| Invalid North Star inputs | 41 |
| Valid TTM / defined growth | 1,611 / 1,414 |
| 2025Q3 like-for-like USD growth | +16.7% (n = 20) |
| Spec card size | 10,932 bytes |
| Rows per layer | CSV = Bronze = Silver = Gold fact = 1,750 |
| Reconciliation | every `rows_differ` = 0 |
| Tests | 28 passed |

## 9. Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Not in the project root, or ran a file directly | `cd C:\Projects\earnings-quality-lens`, then `python -m src.<module>` |
| Prompt has no `(.venv)` / missing packages | Environment not active | `.\.venv\Scripts\Activate.ps1` |
| Activation blocked by policy | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `Fingerprint mismatch` | The CSV was edited or re-saved | Restore it: `git checkout -- data/raw/corporate_income_statement.csv` |
| Git shows `:` or `(END)` | Output opened in a pager | Press `q` |
| A generated doc shows as modified with no real change | Line endings | Scripts write LF; `.gitattributes` normalises; re-run the script |
| DuckDB "file is being used by another process" | Database open elsewhere (e.g. a viewer) | Close the other program, re-run |
| Created a wrong branch | Typo or example command | `git switch main`, then `git branch -d wrong-name` |

## 10. Daily Git routine
```powershell
git switch main
git pull
git switch -c phase-06-eda main
git add src\new_file.py
git commit -m "feat(scope): what changed"
git push -u origin phase-06-eda
git switch main
git merge phase-06-eda
git push
```
| Command | What it does |
|---|---|
| `git switch main` / `git pull` | Start from the latest finished work |
| `git switch -c phase-06-eda main` | New branch for the next phase (name shown is an example for Phase 6) |
| `git add` / `git commit` | Save a checkpoint with a Conventional Commit message (`feat`, `docs`, `fix`, `chore`) |
| `git push -u origin ...` | Upload the branch to GitHub |
| `git merge` / `git push` | Bring the finished phase into `main` and upload it |