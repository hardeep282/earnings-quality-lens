

# Build Log — Phase 01: Business Understanding
Project: Earnings Quality Lens · Milestone: M1 · Mode: GREENFIELD · Depth: STANDARD
Date(s): 2026-10-07 · Hours: 4 est / ⟨fill in⟩ actual · Status: Complete
Branch / PR: `phase-01-business` · Commit(s): ⟨fill from git log⟩ · Environment: assistant sandbox (pandas) for computed figures; Windows/VS Code for repo

## 1. Objective
Turn "is this growth any good?" into a precise, testable business problem. Serves US1, US2, US4.

## 2. What was covered
- Concepts: income-statement value chain · unit economics by cost structure · degree of operating leverage (1 + F/OI) · log-log elasticity · margin mean reversion (partial adjustment) · MECE issue tree · pre-registration vs p-hacking · confounded natural experiments (TCJA + ASC 606 in 2018)
- Methods: TTM ratio recomputation from summed figures; business-model grouping
- Register: no changes

## 3. What was built (artefacts)
| Artefact | Path | Purpose |
|---|---|---|
| Business understanding | `docs/01_business_understanding.md` | Value chain, unit economics, problem, issue tree, H1–H9, context, stakeholders, question bank |
| Build Log entry | `docs/build_log/phase_01_business.md` | This record |

## 4. Key results
- TTM group operating margins: Semis 53.7% · Software 38.3% · Pharma 33.1% · Financials 24.0% · HW/e-com 17.8% · Energy 11.0% · Retail 5.3% [Computed, USD reporters]
- 9 hypotheses pre-registered (H1–H9), each tied to columns and a test phase
- 2018 identified as a double shock (TCJA + ASC 606) [External]

## 5. Decisions made
| Decision | Options considered | Chosen | Why | Reversible? |
|---|---|---|---|---|
| Primary profit measure | Net income · EBIT · operating income | Operating income | Isolates what management controls | Yes |
| Peer grouping | GICS · business model | Business model (7 groups) | Cost structure drives growth-to-profit conversion | Yes |
| Hypothesis timing | Explore first · pre-register | Pre-register | Prevents p-hacking | No (new ones labelled exploratory) |

## 6. Mistakes, errors and issues
None this phase. Data issues found (not mistakes) are logged under section 11.

## 7. Debugging command sheet
None.

## 8. Validation performed
TTM ratios recomputed from sums (no averaged ratios); latest quarter per company checked (2025-07-31 to 2025-10-31).

## 9. Changes to data and assumptions
No data changes. New assumptions: business-model grouping; action threshold (quintile move or 95% interval breach); cost of false alarm ~3–4 analyst-hours.

## 10. Deviations from plan
Phase split into Part A and Part B for readability.

## 11. Open issues and technical debt
AMZN SG&A mapping (1.6% of revenue) · PLTR/AVGO low ETR · bank "gross margin" construct · 2018 confounding → all to Phase 2/10.

## 12. Cost and resources
US$0.

## 13. Learning notes
Quality is contingent on the decision (Dechow et al., 2010), so the decision had to be fixed first. Operating leverage is undefined near zero profit, which drives the KPI edge-case rules.

## 14. Career capture
- Transferable: value-chain + operating-leverage framing → Beverage (fixed warehouse costs), Retail EPOS; pre-registration → Financial Resilience, Banking AI
- CV bullet (draft): "Framed a growth-quality problem for 23 mega-caps as a MECE issue tree with 9 pre-registered, column-linked hypotheses, identifying a confounded 2018 natural experiment (US tax reform + ASC 606)."
- Interview Q&A: *Why operating income?* Management-controlled. *What's DOL?* 1 + F/OI. *Why pre-register?* So significance can't be manufactured after seeing data.

## 15. Sources consulted
Dechow, Ge & Schrand (2010) · Fama & French (2000) · TCJA summaries · ASC 606 (Deloitte DART, KPMG)

## 16. Next steps
Phase 2 — Data Understanding & Quality (branch `phase-02-data`).