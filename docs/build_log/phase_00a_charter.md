


# Build Log — Phase 00A: Project Charter & Decision Register
Project: Earnings Quality Lens · Milestone: M1 · Mode: GREENFIELD · Depth: STANDARD
Date(s): 2026-09-30 → 2026-09-30 · Hours: 2 est / ⟨fill in⟩ actual · Status: Complete
Branch / PR: `phase-00-charter` · Commit(s): ⟨fill from git log⟩ · Environment: assistant sandbox, Python 3 + pandas (scoping scan only)

## 1. Objective
Frame the project before building: brief, charter, value case, user stories, RAID, milestone plan, tool decision register. Serves US1–US7.

## 2. What was covered
- Concepts: walking skeleton (thin end-to-end slice first) · RACI · RAID · value case and build-vs-buy · survivorship/selection bias · portfolio differentiation (hero capability) · fiscal-calendar alignment
- Methods: quick scoping scan of the CSV (shape, hash, currencies, fiscal calendars, identity check, loss quarters, gaps)
- Register: all 37 items decided (see `docs/DECISION_REGISTER.md`); items #7, #12, #13 pending Power BI / Excel licence confirmation

## 3. What was built (artefacts)
| Artefact | Path | Purpose |
|---|---|---|
| Project charter | `docs/00_PROJECT_CHARTER.md` | Brief, charter, value case, requirements, RAID, milestone plan |
| Decision register | `docs/DECISION_REGISTER.md` | USE/PARTIAL/SKIP per component + LangChain decision |
| Interactive roadmap | published HTML artifact (link in chat) | Phase-by-phase navigation |
| Build log index | `docs/BUILD_LOG.md` | Master index |

## 4. Key results
- 1,750 rows × 27 cols; 23 companies; 2005-08-31 → 2025-10-31; SHA-256 prefix `0898c7c5095a153b` [Computed]
- Currencies: USD 1,609 · TWD 81 · CNY 58 · blank 2 [Computed]
- Gross-profit identity fails (>1%) on 95 rows, concentrated in BRK-B (45) and MA (30) [Computed]
- 120 loss quarters; 5 fully-null columns; 3 distinct fiscal calendars [Computed]

## 5. Decisions made
| Decision | Options considered | Chosen | Why | Reversible? |
|---|---|---|---|---|
| Hero capability | Panel forecasting + scoring · Trustworthy text-to-SQL analyst · Anomaly detection | Panel forecasting + Growth-Quality scoring | Unique to this dataset; RAG and multi-agent already proven elsewhere; fits maths-first preference | Yes |
| Business framing | Buy-side research prioritisation · Corporate FP&A peer benchmarking | Buy-side (fictional Alpha Capital Partners) | Clear quarterly decision | Yes |
| Data constraint | Pull FX/SEC/vendor data · CSV only | CSV only (owner's decision) | Everything built from the supplied data; currency-invariant KPI design | Yes |
| LangChain | USE / PARTIAL / SKIP | PARTIAL | Integrations yes; hand-built SQL path for auditability | Yes |
| Multi-agent | Full build / benchmark-first | Benchmark-first | Avoid cloning the beverage stack | Yes |

## 6. Mistakes, errors and issues
- **What happened:** Project brief in the prompt file was left blank.
- **Type:** process/scope
- **Root cause:** Prompt file is a reusable template; per-project fields were not filled before sending.
- **How it was detected:** START step 1 (reading the brief).
- **Fix applied:** Brief filled with [Assumed] values; critical unknowns raised at the gate and answered.
- **Prevention:** Keep a filled brief per project and paste it with the prompt.
- **Impact:** One revision (v0.2) after the CSV-only constraint was set; ~20 minutes.

## 7. Debugging command sheet
None (no live troubleshooting this phase).

## 8. Validation performed
Scoping counts re-run twice with consistent results; per-company row counts sum to 1,750.

## 9. Changes to data and assumptions
No data changes. Assumptions A1–A5 recorded in the charter RAID log.

## 10. Deviations from plan
**Revision v0.2:** owner set a CSV-only constraint. Removed FX API, SEC XBRL tie-out, SEC MD&A corpus and vendor refresh. Replaced with a currency-invariant KPI design, internal accounting-identity checks, a methodology-docs RAG corpus, and a quarter-replay automation demo. Plan ≈177 h. Phase 0 split into Part A (framing) and Part B (repo and environment).

## 11. Open issues and technical debt
Resolved: LLM provider = Anthropic (own key); data source = static CSV only. Still open: hours budget, AWS account, Power BI availability.

## 12. Cost and resources
US$0 cloud · US$0 LLM API · 0 GPU hours.

## 13. Learning notes
Survivorship bias is the first thing an interviewer with markets experience will probe on this dataset: 23 companies selected *because* they succeeded cannot tell you what predicts success.

## 14. Career capture
- Transferable: charter/RAID/value-case template reusable for the Banking AI and Financial Resilience projects
- CV bullet (draft): "Scoped a quarterly earnings-analytics product for 23 global mega-caps (1,750 company-quarters, 2005–2025), defining 7 user stories, measurable acceptance thresholds and a 37-item build/skip decision register."
- Interview Q&A: *Why not predict stock returns?* No price data, and not the decision. *Biggest flaw in the data?* Survivorship bias. *Why build if Bloomberg exists?* Buy the data, build the method.

## 15. Sources consulted
- https://www.alphavantage.co/documentation/
- https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/

## 16. Next steps
Phase 0B: repository, environment, first push.