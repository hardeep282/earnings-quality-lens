


# Earnings Quality Lens — Project Charter (Phase 0)

> **Status:** v0.3 · 2026-10-06 · approved for build; CSV-only constraint applied; open items: hours budget, AWS account, Power BI availability
> **Operating constraint (stated by owner):** the supplied CSV is the only data source. No data is pulled from the internet at any stage. The Anthropic API is used only for the AI layer (it never supplies data or numbers).
> **Data label:** REAL public-company data (vendor-normalised quarterly income statements). **Client is FICTIONAL.**
> **Disclaimer:** Portfolio analytics project. Not investment advice and not a trading signal.

Evidence tags: [Observed] seen in the data · [Computed] by code · [Inferred] reasoned · [Assumed] stated assumption · [External: source]

---

## 1. Project brief

| Field | Value |
|---|---|
| Project name | **Earnings Quality Lens** — repo https://github.com/hardeep282/earnings-quality-lens |
| Mode | GREENFIELD |
| Scope | FULL (AWS deployment requested) |
| Domain | Public-equity fundamental research (buy-side), cross-sector mega-caps |
| Business context | *Alpha Capital Partners* (fictional), a long-only equity research team covering global mega-caps; re-prioritises analyst coverage every earnings season [Assumed] |
| Decision to support | Within 48 h of each earnings season, the Head of Research decides which companies go on the **deep-dive priority list** (quality improving or deteriorating) and where analyst hours are reallocated. Quarterly cadence. |
| Primary audience | Head of Equity Research / Portfolio Manager; secondary: hiring managers |
| Dataset | `corporate_income_statement.csv` — 1,750 rows × 27 cols, 23 companies, fiscal quarters 2005-08-31 → 2025-10-31 [Computed]; course-supplied extract; field names match Alpha Vantage `INCOME_STATEMENT` [Observed]. Static snapshot: no vendor key, no refresh from source |
| Unstructured data | None, and none will be fetched. The only text corpus is the project's own methodology docs (KPI spec cards, data dictionary, model cards) — register #18 |
| Existing assets | None (planning notes only) |
| Tool constraints | CSV-only data (see constraint above) · LLM: owner's Anthropic API key · Power BI / Excel licence: to confirm |
| Deployment target | AWS EC2 + Docker Compose + Nginx + Certbot, one subdomain per project |
| Domain name | Not yet (register only when close to deployment) |
| Regulatory regime | No personal data (public filings) → UK GDPR / DPDP exposure minimal. Research-publication caution: outputs labelled "not investment advice" |
| Target roles | Data Scientist / Decision Scientist · Commercial/Financial Analyst · Analytics Engineer · GenAI Engineer (secondary) |
| Target level | Senior Analyst / mid-level Data Scientist [Assumed] |
| Hero capability | **Panel forecasting with calibrated uncertainty + a robust Growth-Quality scoring model** (statistics- and algorithm-heavy decision science) |
| Portfolio map | Beverage distribution → forecasting + ML + *agentic deep search* (canonical multi-agent) · BA airline → *RAG* over competitor corpus · Automobile → classic ML, no GenAI (by design) · Online Retail / Market Basket → association rules · Banking AI → commercial risk & compliance · Financial Resilience → household regression (R) · Agentic L2C → voice negotiation agent |
| Data realism | Real, public (vendor-normalised to SEC GAAP/IFRS taxonomies) |
| Execution env | Windows · PowerShell · VS Code · Python 3.12.3 (venv) · Git 2.42 · Docker: to check |
| Hours budget | To confirm — plan below assumes ≈177 h [Assumed] |
| Depth | STANDARD overall; hero phases (6–10) DEEP; reused AI stack LEAN-to-STANDARD |

### Why this hero capability (portfolio differentiation)
Other projects in this portfolio already prove agentic orchestration (beverage distribution) and RAG (airline). Cloning either here would read as a template. What this dataset uniquely supports is a **20-year, 23-entity panel** — the right raw material for time-series econometrics, forecasting with honest prediction intervals, and a composite score whose robustness can be tested mathematically. The project therefore leads with statistics and algorithms rather than software engineering.

---

## 2. What the data already tells us about scope (quick scoping scan, not the Phase 2 audit)

| Observation | Evidence | Consequence for the plan |
|---|---|---|
| 23 companies chosen because they are *today's* mega-caps | Ticker list [Observed] | **Survivorship/selection bias.** No claim that any metric "predicts becoming a winner". Findings describe these 23 only. |
| 3 reporting currencies | USD 1,609 · TWD 81 (TSM) · CNY 58 (BABA) · 2 blank (PLTR 2019) [Computed] | **No FX data available.** Design is currency-invariant: margins, intensities and growth are computed within each company in its own currency. TSM/BABA growth is therefore local-currency (≈ constant-currency) growth. Cross-company absolute totals and size rankings use USD reporters only; TSM/BABA are excluded from those and flagged |
| Financials behave differently | Gross-profit identity (Revenue − CostOfRevenue = GrossProfit) fails >1% on 95 rows: BRK-B 45, MA 30, BABA 7, V 5, META 4 … [Computed] | Sector-aware KPI rules; banks/insurers/payment networks get their own peer group |
| Fiscal calendars differ | Quarter-end months: Mar/Jun/Sep/Dec for most; Jan/Apr/Jul/Oct for NVDA, AVGO, HD, WMT; Feb/May/Aug/Nov for COST, ORCL [Computed] | Calendar-alignment rule required before any cross-sectional comparison |
| Uneven history | PLTR 27 quarters (from 2019), BABA 58, META 63; most 81 [Computed] | Unbalanced panel → model choices must handle it |
| Loss-making quarters | 120 rows with net income < 0 (TSLA 43, PLTR 15, AMZN 8 …) [Computed] | Growth rates on negative bases are undefined → KPI edge-case rules |
| Empty columns | 5 columns 100% null (investmentIncomeNet, nonInterestIncome, comprehensiveIncomeNetOfTax, interestAndDebtExpense, depreciation) [Computed] | Dropped in Silver, logged |
| Two gaps in history | TSLA 2007-12 and 2008-09 spacing > 100 days [Computed] | Gap handling in time-series phases |
| Income statement only | No balance sheet, cash flow, share count or price [Observed] | ROIC, FCF, DSO, EPS, valuation, stock returns = **Needs data** (would require balance-sheet, cash-flow and price data — out of scope) |

---

## 3. Charter

**Objective.** Give a research team a repeatable, quarterly view of *which mega-caps are growing efficiently and which are not*, with forecasts that say how uncertain they are — computed from reported numbers, never from an LLM's memory.

**Stakeholders (RACI)**

| Activity | Head of Research (sponsor) | Analytics lead | Sector analysts | PM | Compliance | Hiring panel |
|---|---|---|---|---|---|---|
| Define decision & KPIs | A | R | C | C | I | I |
| Data pipeline & Gold layer | I | A/R | I | I | I | I |
| Models & scoring | C | A/R | C | C | I | I |
| Dashboard & briefs | A | R | C | C | C | I |
| AI analyst (NL Q&A) | A | R | C | I | C | I |
| Go-live & monitoring | I | A/R | I | I | I | I |

**In scope:** quarterly income-statement analytics for 23 companies from the supplied CSV only; KPI/semantic layer; EDA, inference, regression, forecasting, scoring, anomaly detection; simulated experiment for the product itself; Power BI (if available) / Streamlit; text-to-SQL analyst with numeric-accuracy evals; lean RAG over the project's own methodology docs; FastAPI + MCP; Docker; AWS.

**Out of scope (deliberate non-goals):** any internet data source (FX rates, SEC filings, vendor refresh, news); price or return prediction (no price data, and not the decision); trading signals; balance-sheet and cash-flow KPIs (Needs data — possible v2); real-time streaming; companies outside the 23.

**Success criteria**

| Type | Criterion | Threshold |
|---|---|---|
| Business | Scoring ranks are robust to reasonable weight changes | median Spearman ρ ≥ 0.80 across Monte Carlo weight draws |
| Business | Forecasts beat the naive benchmark | ≥ 10% lower MASE than seasonal-naive on rolling-origin backtest |
| Business | Earnings-season brief is trustworthy | 0 numeric errors (automated fact-check) |
| Technical | Data integrity | Bronze→Silver→Gold row counts reconcile; accounting identities hold within 1% outside documented sector exceptions |
| Technical | Honest uncertainty | 80% prediction intervals cover 75–85% of actuals in backtest |
| Technical | AI analyst | text-to-SQL execution accuracy ≥ 90%; numeric accuracy 100% in exec outputs |
| Technical | Live service | p95 < 2 s on KPI endpoints; uptime check green; billing alarm set |

**Constraints:** solo build; free/low-cost tooling; CSV-only data; AWS credit-based free plan for new accounts (see RAID R5).

**Delivery lifecycle (mirrors industry):** discovery (Ph 0–1) → requirements (Ph 0) → data (Ph 2, 3, 5) → build (Ph 4, 6–18) → UAT (panel reviews + eval gates) → deploy (Ph 19–20) → hypercare (monitoring, 2 weeks) → handover (Ph 22).

---

## 4. Value case & build vs buy

**Current state [Assumed, fictional client]:** after each earnings season an analyst copies each company's statements into Excel, recomputes margins and growth by hand, and writes a note. Rough effort ≈ 3–4 analyst-hours per company → ~70–90 hours per quarter for 23 names. Pain points: inconsistent formulas across analysts (averaged ratios, mismatched fiscal calendars), no forecast uncertainty, late detection of deteriorating quality.

**Cost of the status quo:** analyst time, plus the risk of a slow reaction to margin compression in a held name.

**Value hypothesis:** an automated pipeline cuts routine prep to minutes, standardises definitions (one KPI definition, used everywhere), and flags breaks from a company's own history earlier. Impact will be sized with explicit ranges in Phase 10, not claimed here.

**Build vs buy:**
| Option | Strength | Weakness |
|---|---|---|
| Buy a terminal/data platform (Bloomberg, FactSet, Capital IQ, Koyfin) | Best raw data, consensus estimates, ratios out of the box | Per-seat licensing; the firm's own scoring method and uncertainty-aware forecasts are not built in; limited transparency of derived metrics |
| **Build on top of bought/public data (chosen)** | House methodology, transparent maths, integrates with internal notes and AI assistants | Must maintain pipeline and models |

In a real firm the sensible answer is *buy the data, build the method*. This project mirrors that: the data is a vendor-format extract; the value is in the scoring, forecasting and governance layer.

**Running cost of the solution [Assumed, verified in Phase 20]:** one small EC2 instance with Docker Compose; LLM calls only for NL Q&A and briefs (cents per query at small-model pricing). Ceiling set in the NFRs below.

---

## 5. Requirements

**User stories**
| ID | Story | Acceptance criteria |
|---|---|---|
| US1 | As Head of Research, I need a ranked Growth-Quality Score per company with its drivers, so I can reprioritise coverage within 48 h of earnings | Score + driver decomposition per company-quarter; rank stability reported |
| US2 | As a PM, I need revenue and operating-margin forecasts for the next 4 quarters with 80%/95% intervals, so I can stress-test theses | Backtested vs seasonal-naive; interval coverage reported |
| US3 | As an analyst, I need calendar-aligned peer benchmarks with ratios recomputed at every level, so comparisons are fair | No averaged ratios; currency-invariant and calendar rules documented and tested |
| US4 | As Risk, I need an alert when a company's margins or earnings break from its own history, so I can investigate early | Anomaly flags with explanation; false-alarm rate reported |
| US5 | As an analyst, I want to ask plain-English questions and get exact numbers with the SQL shown | Execution accuracy ≥ 90% on golden set; read-only role |
| US6 | As Head of Research, I want an auto-drafted earnings-season brief where every number is verified | Fact-check blocks publication on any mismatch |
| US7 | As a hiring manager, I want the live app to load fast and show one insight in 30 s | Cold load < 3 s; landing insight above the fold |

**Non-functional requirements**
| NFR | Target |
|---|---|
| Refresh | File-drop trigger (new quarter CSV) + manual run; demonstrated by quarter-replay |
| Latency | KPI API p95 < 2 s; AI answers < 10 s |
| Access | Read-only DB role for AI components; API key on write/admin endpoints |
| Cost ceiling | ≤ US$20/month cloud, ≤ US$5/month LLM [Assumed — confirm] |
| Reliability | Uptime check + CloudWatch alarm; documented rollback |
| Reproducibility | Pinned env, fixed seeds, data snapshots with hashes |

---

## 6. RAID log

| ID | Type | Item | Mitigation / owner |
|---|---|---|---|
| R1 | Risk | Survivorship/selection bias (23 current winners) | Scope language; no predictive-of-success claims |
| R2 | Risk | Vendor data errors or silent restatements (no external source to tie out against) | Internal accounting-identity checks (GP = Rev − COGS; OpInc = GP − OpEx; EBITDA = EBIT + D&A; NI ≈ PBT − tax) + snapshot hash. Residual risk accepted and disclosed |
| R3 | Risk | Tiny cross-section (n = 23) → overfitting | Panel methods, rolling-origin CV, report uncertainty |
| R4 | Risk | Data is frozen at 2025-10; no refresh path | Automation demonstrated by a **quarter-replay**: withhold the latest quarter, then drop it in as a "new" file and run the full pipeline |
| R5 | Risk | AWS credit burn (new accounts are on a 6-month credit-based free plan) | Budgets alarm on day 1; smallest instance; teardown doc |
| R6 | Risk | Scope creep across 22 phases | Time-box per phase; LEAN on reused components |
| R7 | Risk | LLM states a wrong number | Numeric accuracy is release-blocking; LLM never generates numbers |
| A1 | Assumption | Course-supplied extract (Data Career School, Week 5) in Alpha Vantage `INCOME_STATEMENT` format; SHA-256 `0898C7C5…61DA30` verified on owner's laptop | Provenance recorded in README |
| A2 | Assumption | Values are in whole currency units (not thousands) | Check in Phase 2 |
| A3 | Assumption | Client and value case are fictional | Labelled everywhere |
| A4 | Assumption | Fiscal quarters mapped to calendar quarters by period-end month | Rule finalised in Phase 2/5 |
| A5 | Assumption | Within-company ratios and growth are currency-invariant; TSM/BABA stay in reported currency | Rule fixed in Phase 2/5 |
| I1 | Issue | 5 fully-null columns | Drop in Silver |
| I2 | Issue | Gross-profit identity fails for financials | Sector-aware rules |
| I3 | Issue | Mixed currencies; 2 blank currency rows | Currency-invariant design; blank PLTR 2019 rows set to USD (all other PLTR rows are USD) and logged |
| D1 | Dependency | None for data (static CSV) | — |
| D2 | Dependency | AWS account | Owner |
| D3 | Dependency | Anthropic API key (owner has one) | Owner; stored in `.env`, never committed |
| D4 | Dependency | Domain name | Owner (later) |
| D5 | Dependency | Power BI Desktop (Windows) | Owner |

---

## 7. Milestone plan (hours are estimates; revisited at every gate)

| Milestone | Phases | Est. hours | Panel review |
|---|---|---|---|
| M1 Walking skeleton | 0, 1, 2, 3 (North Star), 5 (Bronze→Gold, one fact table), baseline forecast, Docker stub deployed | 26 | Review 1 |
| M2 Insight engine | 3 full, 4, 5 full, 6, 7, 8, 9, 10 | 70 | Review 2 |
| M3 Decision surface | 11 | 10 | — |
| M4 AI layer | 12–18 (per register; RAG trimmed to lean) | 42 | Review 3 |
| M5 Production | 19, 20 | 16 | — |
| M6 Story & package | 21, 22 | 13 | Review 4 |
| **Total** | | **≈177 h** (+15% contingency ≈ 204 h) | |

**Hero depth plan (DEEP):**
- Ph 6: STL decomposition, ACF/PACF, ADF + KPSS per company; structural breaks (e.g. 2008, 2020, the 2023 AI cycle).
- Ph 7: panel-aware tests; effect sizes; FDR control across 23 companies.
- Ph 8: panel regression (pooled vs fixed effects vs random effects, Hausman test); log-log **operating-leverage elasticity**; HC3/clustered errors.
- Ph 9: seasonal-naive → ETS → SARIMA → global LightGBM with lags → PyTorch MLP with company embeddings; rolling-origin backtest; **conformal prediction intervals**; MASE/WAPE.
- Ph 10: Growth-Quality Score as multi-criteria decision analysis (z-scored components, PCA-weights vs expert weights, Monte Carlo weight robustness); DiD/synthetic-control candidate on the **2017 US Tax Cuts and Jobs Act** effect on effective tax rate, computed entirely from the CSV (incomeTaxExpense / incomeBeforeTax; US filers vs TSM/BABA as controls — weak control group, stated honestly); simulated A/B for the alert product.

---

## 8. Sources consulted (Phase 0)
- Alpha Vantage fundamental data docs (INCOME_STATEMENT, normalised to SEC GAAP/IFRS taxonomies): https://www.alphavantage.co/documentation/
- AWS Free Tier changes of 15 July 2025 (credit-based free plan for new accounts): https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/