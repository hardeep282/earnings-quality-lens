



# Build Log — Phase 00B: Repository, Environment & First Push
Project: Earnings Quality Lens · Milestone: M1 · Mode: GREENFIELD · Depth: STANDARD
Date(s): 2026-09-30 → 2026-10-06 · Hours: 2 est / ⟨fill in⟩ actual · Status: Complete
Branch / PR: `main` (initial commit), `phase-00-charter` (docs) · Commit(s): ⟨fill from git log⟩ · Environment: Windows, PowerShell, VS Code, Python 3.12.3, Git 2.42.0

## 1. Objective
Create a reproducible project skeleton, an isolated Python environment, version control, and the public GitHub repo.

## 2. What was covered
- Concepts: virtual environments (per-project isolation) · requirements.in vs pinned requirements.txt · .gitignore (secrets and generated artefacts out of Git) · .gitattributes (line endings; byte-exact CSV keeps its SHA-256) · Conventional Commits · remotes and upstream tracking · data lineage via file hash
- Tools: Python 3.12.3 venv, pip 26.2.1, Git 2.42.0, GitHub
- pandas 3.0 note: default string dtype and always-on Copy-on-Write (no chained assignment)

## 3. What was built (artefacts)
| Artefact | Path | Purpose |
|---|---|---|
| Folder skeleton + .gitkeep files | repo root | Medallion data folders, src, app, AI layer, docs, CI |
| Virtual environment | `.venv/` (git-ignored) | Isolated Python 3.12.3 |
| Package lists | `requirements.in`, `requirements.txt` | Chosen packages; exact pinned versions |
| Git rules | `.gitignore`, `.gitattributes` | Exclusions; line-ending and CSV byte protection |
| Settings template | `.env.example` (committed), `.env` (ignored) | Config without secrets in Git |
| README | `README.md` | Summary, data provenance + hash, setup |
| Raw data | `data/raw/corporate_income_statement.csv` | Bronze source (renamed from `corporate_income_statement (1).csv`) |

## 4. Key results
- SHA-256 of raw CSV on laptop = `0898C7C5095A153B3D829ECFD788533722417A706A7F31ADB23121842561DA30`, identical to the file analysed in Phase 0A [From my local run]
- Pinned: pandas 3.0.6 · numpy 2.5.3 · duckdb 1.5.6 · matplotlib 3.11.2 · python-dotenv 1.2.3 · streamlit 1.64.0 · ipykernel 7.4.0 · pytest 9.1.1 · ruff 0.16.9 [From my local run]
- `git status` before first commit listed neither `.venv/` nor `.env` → .gitignore verified [From my local run]
- Repo live: https://github.com/hardeep282/earnings-quality-lens

## 5. Decisions made
| Decision | Options considered | Chosen | Why | Reversible? |
|---|---|---|---|---|
| Python version | 3.14 (default), 3.12 | 3.12 | Broad wheel availability for ML/AI libraries | Yes |
| Pinning method | `pip freeze` · pin direct deps only | Direct deps only (generated from installed versions) | `pip freeze` pins Windows-only transitive packages that break the Linux Docker image | Yes |
| Commit raw CSV | Commit · ignore | Commit | 409 KB, public figures; enables end-to-end reproducibility | Yes |
| Project root | New folder · existing `C:\Projects` | `C:\Projects` | Owner's standard location; not OneDrive-synced | — |

## 6. Mistakes, errors and issues
**Issue 1 — Another project's venv was active**
- **What happened:** `py -0` showed "Active virtual environment"; `$env:VIRTUAL_ENV` = `C:\Projects\l2c-agent\.venv`
- **Type:** environment/setup
- **Root cause:** VS Code carried the L2C project's interpreter into this terminal
- **How it was detected:** `py -0` output, confirmed with `$env:VIRTUAL_ENV`
- **Fix applied:** created `.venv` with `py -3.12`, activated it, selected it via *Python: Select Interpreter*; new terminals now auto-activate it
- **Prevention:** check `$env:VIRTUAL_ENV` before any `pip install` in a new project
- **Impact:** none; caught before any package was installed into the wrong environment

**Issue 2 — Verification filter didn't hide the venv**
- **What happened:** `tree /F /A | Select-String -NotMatch "\.venv"` still printed thousands of venv files
- **Type:** assistant error
- **Root cause:** the filter removes only lines containing the text `.venv`; files inside the venv appear on lines without that text
- **How it was detected:** pasted output
- **Fix applied:** `Get-ChildItem -Recurse -Force -File | Where-Object FullName -notmatch '\\\.venv\\' | Resolve-Path -Relative`
- **Prevention:** filter on full paths, not on display lines
- **Impact:** ~5 minutes

**Issue 3 — `git push` → "Repository not found"**
- **What happened:** `remote: Repository not found. fatal: repository 'https://github.com/hardeep282/earnings-quality-lens.git/' not found`
- **Type:** process order
- **Root cause:** push attempted before the repo was created on GitHub; `git push` does not create remote repos
- **How it was detected:** push error; the URL returned 404 in the browser
- **Fix applied:** created the empty repo at github.com/new (no README/.gitignore/license), re-ran `git push -u origin main`
- **Prevention:** create the empty remote first, nothing ticked
- **Impact:** ~10 minutes; no data or history affected

**Issue 4 — Phase 0 docs zip could not be downloaded**
- **What happened:** `Expand-Archive` failed (path not found); the file card was not visible in the chat interface
- **Type:** environment/setup (tooling)
- **Root cause:** the download card didn't render; a literal placeholder path was also pasted once
- **How it was detected:** file search found no zip; card confirmed not visible
- **Fix applied:** docs created directly in VS Code (`code <file>` → paste → save)
- **Prevention:** deliver repo files as copy-paste blocks; no angle-bracket placeholders in runnable commands
- **Impact:** ~20 minutes

## 7. Debugging command sheet
| What the step is | Command | What it does |
|---|---|---|
| Find the active venv | `$env:VIRTUAL_ENV` | Prints the active environment's folder |
| Create the project venv | `py -3.12 -m venv .venv` | Builds an isolated Python 3.12 in `.venv` |
| Activate it | `.\.venv\Scripts\Activate.ps1` | Switches this terminal to the project's Python |
| Prove which Python runs | `python -c "import sys; print(sys.executable)"` | Must end in `earnings-quality-lens\.venv\Scripts\python.exe` |
| List project files without the venv | `Get-ChildItem -Recurse -Force -File \| Where-Object FullName -notmatch '\\\.venv\\' \| Resolve-Path -Relative` | Clean file inventory |
| Check the remote URL | `git remote -v` | Shows where Git pushes |
| Fix the remote URL (if needed) | `git remote set-url origin <url>` | Replaces the stored address |
| Check the signed-in GitHub account | `git credential-manager github list` | Shows stored accounts |
| Find a downloaded file under your user folder | `Get-ChildItem $HOME -Recurse -Filter "*name*" -ErrorAction SilentlyContinue \| Select-Object FullName` | Prints full paths of matching files |
| First push | `git push -u origin main` | Uploads and links `main` to `origin/main` |

## 8. Validation performed
CSV hash match · venv path check · `git status` exclusion check · successful push (16 objects).

## 9. Changes to data and assumptions
Raw file renamed `corporate_income_statement (1).csv` → `corporate_income_statement.csv` (bytes unchanged; hash verified). A1 updated: course-supplied extract in Alpha Vantage format.

## 10. Deviations from plan
Docker check deferred to the walking-skeleton step, where the Dockerfile is first written.

## 11. Open issues and technical debt
Docker install check · split runtime vs dev requirements (Phase 19) · hours budget, AWS account, Power BI availability.

## 12. Cost and resources
US$0.

## 13. Learning notes
Git hides empty folders (hence `.gitkeep`). `.gitignore` must exist before the first `git add`. A file hash is the cheapest lineage control there is.

## 14. Career capture
- Transferable: identical setup applies to every portfolio repo; the `.gitattributes` CSV rule protects any dataset fingerprint
- CV bullet (draft): "Set up a reproducible analytics repository (isolated Python 3.12 environment, pinned dependencies, SHA-256 data lineage, Conventional Commits, branch-per-phase workflow)."
- Interview Q&A: *Why not commit `.venv`?* It's machine-specific and rebuildable from requirements. *Why pin versions?* So results reproduce identically on another machine. *What if an API key is pushed?* Treat it as compromised: revoke and rotate immediately; deleting the commit isn't enough.

## 15. Sources consulted
- https://docs.python.org/3/library/venv.html
- https://pip.pypa.io/en/stable/reference/requirements-file-format/
- https://git-scm.com/docs/gitignore · https://git-scm.com/docs/gitattributes
- https://www.conventionalcommits.org/

## 16. Next steps
Commit Phase 0 docs, merge to main → Phase 1 (business understanding).