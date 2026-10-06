

# Phase 1 — Business Understanding

> Earnings Quality Lens · Milestone M1 · Status: complete · Data: CSV-only (real public figures; client fictional) · Not investment advice
> Evidence tags: [Observed] · [Computed] · [Inferred] · [Assumed] · [External: source]

## 1. Value chain: where every column sits

| Step | Line item | Column(s) | Tag |
|---|---|---|---|
| Sales | Revenue | `totalRevenue` | Direct |
| − Cost of making/delivering | Cost of revenue | `costOfRevenue` (= `costofGoodsAndServicesSold`) | Direct |
| = | Gross profit | `grossProfit` | Direct (check: Revenue − COGS) |
| − Running the business | R&D, SG&A | `researchAndDevelopment`, `sellingGeneralAndAdministrative` (≈ `operatingExpenses`) | Direct |
| = | **Operating income** (core business) | `operatingIncome` | Direct |
| ± Non-core | Interest, other | `interestIncome`, `interestExpense`, `netInterestIncome`, `otherNonOperatingIncome` | Direct (sparse) |
| = | Pre-tax income | `incomeBeforeTax`; `ebit` ≈ pre-tax + interest expense | Direct |
| − Tax | Income tax | `incomeTaxExpense` | Direct |
| = | Net income | `netIncome` | Direct |
| Add-back | D&A | `depreciationAndAmortization`; `ebitda` = `ebit` + D&A | Direct (check) |

Operating income (not EBIT, not net income) is the primary measure of growth quality: it isolates what management controls.

## 2. Unit economics by business model (TTM to Jul–Oct 2025)

Ratios recomputed from summed figures; group figures use USD reporters only (TSM, BABA excluded) [Computed]. Grouping by cost structure [Assumed]; differs from GICS.

| Business model | Companies | TTM operating margin | Margin driver |
|---|---|---|---|
| Semiconductors | NVDA, AVGO, TSM | 53.7% | Pricing power; heavy fixed R&D |
| Software & internet | MSFT, GOOG, META, ORCL, PLTR, NFLX | 38.3% | Near-zero marginal cost → high operating leverage |
| Pharma | LLY, JNJ | 33.1% | Patent-protected pricing; R&D 17–22% of revenue |
| Financials & payments | JPM, BRK-B, V, MA | 24.0% | Network effects (V, MA ≈ 60%); "gross profit" not meaningful for banks/insurers |
| Consumer hardware & e-commerce | AAPL, AMZN, BABA, TSLA | 17.8% | Mix of services and physical goods |
| Energy | XOM | 11.0% | Commodity prices |
| Retail | WMT, COST, HD | 5.3% | Volume; COST op. margin 3.8% |

Flags for Phase 2 [Observed]: AMZN SG&A = 1.6% of revenue (vendor line-item mapping; not comparable across companies) · PLTR ETR 1.5%, AVGO 4.1% (loss carry-forwards / tax benefits) · bank "gross margin" is a vendor construct.

## 3. Operating leverage

OI = R·(1 − v) − F → **DOL = %ΔOI / %ΔR = 1 + F / OI**. With fixed costs, profit grows faster than revenue; DOL explodes as OI → 0 and is undefined/negative when OI < 0 (102 rows). Estimated in Phase 8 as β in ln(OI) = α + β·ln(R) on profitable periods.

## 4. Problem statement

| Element | Definition |
|---|---|
| Problem | Growth quality judged by hand each earnings season: inconsistent formulas, no uncertainty, slow detection of deterioration |
| Decision | Which companies move onto/off the deep-dive priority list; where analyst hours go |
| Decision-maker | Head of Equity Research (fictional) |
| Frequency | Quarterly, within 48 h of results |
| Action threshold | Growth-Quality Score moves ≥ 1 quintile, or operating margin falls outside its own 95% forecast interval [Assumed; finalised Ph 3] |
| Cost of a wrong call | Missed deterioration in a held name vs ~3–4 wasted analyst-hours per false alarm [Assumed] |

## 5. Issue tree — "Is this company's growth high-quality?"

| Branch | Sub-questions | Measures | Hypotheses |
|---|---|---|---|
| 1. Is growth real and durable? | Trend vs one-off · stability · structural breaks | TTM revenue growth, volatility, seasonality | H6, H9 |
| 2. Does growth turn into operating profit? | Gross margin · cost scaling · operating leverage | GM, R&D/SG&A elasticity, β | H1, H3, H4, H8 |
| 3. Is the bottom line clean? | Non-operating items · tax · losses | ETR, interest, loss quarters | H7 |
| 4. Is it predictable enough to plan on? | Forecast error · mean reversion · amplification | MASE, AR(1), CV ratios | H2, H5 |

## 6. Pre-registered hypotheses (fixed before testing)

| ID | Hypothesis | Columns | Test (phase) | Decision use |
|---|---|---|---|---|
| H1 | OI grows faster than revenue (β > 1) for most companies | OI, revenue | Within-company log-log elasticity (8) | Who gains most from growth |
| H2 | Operating margins revert toward each company's own mean | OI/revenue | AR(1)/partial adjustment (7–8) | Record margins less trustworthy |
| H3 | SG&A grows slower than revenue (elasticity < 1) | SG&A, revenue | Log-log elasticity, comparable SG&A only (8) | Efficient vs bloated growth |
| H4 | Higher R&D intensity goes with higher gross margin (association) | R&D, GP, revenue | Panel regression, company effects (8) | Does R&D buy pricing power |
| H5 | OI more volatile than revenue (amplification) for most companies | OI, revenue | Paired Wilcoxon on CVs of YoY growth (7) | Earnings vs sales risk |
| H6 | Retail and consumer hardware more seasonal than software | revenue, date | STL seasonal strength by group (6–7) | Seasonal forecasting where needed |
| H7 | US filers' ETR fell after 2018 vs TSM/BABA, excl. Q4-2017 one-offs | tax, pre-tax income | Difference-in-differences (10) | Tax- vs operations-driven profit growth |
| H8 | In high-growth quarters, op. margin expands more often than it compresses | revenue YoY, OI/revenue | Sign/binomial test (7) | Is growth alone a quality signal |
| H9 | 2020 and the 2023 AI cycle create level shifts in semiconductor revenue | revenue, date | Structural-break tests (6) | Forecasts must handle regimes |

Caveats: survivorship bias can itself create apparent mean reversion (H2); H4 and H8 are associations, not causes.

## 7. Industry and regulatory context

| Event | Effect on this data | Handling |
|---|---|---|
| US Tax Cuts and Jobs Act: corporate rate 35% → 21% for taxable years beginning after 31 Dec 2017; deferred-tax remeasurement at 31 Dec 2017; blended rates for fiscal-year filers [External: TCJA summaries] | ETR level shift from 2018; one-off spikes around Q4 2017; NVDA, WMT, HD, COST, ORCL, AVGO transition differently | H7 design excludes transition quarters |
| ASC 606 revenue recognition: effective for public companies' fiscal years beginning after 15 Dec 2017 [External: Deloitte DART, KPMG] | Possible revenue-definition changes in 2018 for US GAAP filers | **Confounder:** 2018 has a tax shock and an accounting shock at once; any 2018 revenue break may be accounting, not economics |
| COVID-19 (2020) | Demand shocks of opposite sign by sector | Structural-break tests (H9) |
| AI capex cycle (2023–) | Semiconductor revenue regime change | H9; forecasting regimes |
| Data rules | Public company figures; no personal data → UK GDPR / DPDP exposure minimal | Outputs labelled "not investment advice" |

## 8. Stakeholder simulation

| Stakeholder | Cares about | Rejects the output if… | Does differently with it |
|---|---|---|---|
| Head of Research (sponsor) | Where to spend analyst hours | Rankings flip with small weight changes; no explanation of drivers | Reallocates coverage within 48 h of results |
| Portfolio Manager | Downside risk in held names | Forecasts have no intervals or don't beat naive | Stress-tests theses with 80/95% ranges |
| Sector analyst | Fair peer comparison | Averaged ratios, mismatched fiscal calendars, banks compared on gross margin | Starts notes from standard numbers |
| Risk / Compliance | No misleading claims | LLM-generated numbers; causal claims without design; no disclaimer | Approves distribution with fact-check evidence |
| Hiring manager (portfolio) | Judgement and rigour | No business question, no baseline, inflated claims | Shortlists |

## 9. Analytical question bank

| Type | Question | Phase |
|---|---|---|
| Descriptive | How have revenue, operating margin and net margin evolved per company and group (TTM)? | 6 |
| Descriptive | Which companies had the most loss-making quarters, and when? | 6 |
| Descriptive | How concentrated is revenue among the USD reporters (top-5 share)? | 6 |
| Descriptive | How seasonal is each company's revenue? | 6 |
| Diagnostic | Which costs (COGS, R&D, SG&A) explain margin changes per company? | 6–8 |
| Diagnostic | Did margins expand or compress in high-growth periods? (H8) | 7 |
| Diagnostic | How much of 2018 profit growth was tax rather than operations? (H7) | 10 |
| Diagnostic | Where are the structural breaks, and are they accounting or economics? | 6 |
| Predictive | Revenue and operating margin for the next 4 quarters, with intervals | 9 |
| Predictive | Which companies are most likely to see margin compression next year? | 9 |
| Predictive | How far will current record margins revert? (H2) | 8–9 |
| Prescriptive | Which companies should top the deep-dive list this quarter? | 10 |
| Prescriptive | What alert thresholds minimise missed deteriorations for a fixed analyst budget? | 10 |
| Prescriptive | Would a quality-alert product change analyst decisions? (simulated A/B) | 10 |

## Sources
- Dechow, P., Ge, W. & Schrand, C. (2010). Understanding earnings quality. *Journal of Accounting and Economics*. doi:10.1016/j.jacceco.2010.09.001
- Fama, E. & French, K. (2000). Forecasting profitability and earnings. *Journal of Business* 73(2). doi:10.1086/209638
- Tax Cuts and Jobs Act summaries (Wilson Sonsini; Quarles; Elliott Davis on IRC §15 fiscal-year blending)
- ASC 606 effective dates: Deloitte DART; KPMG Financial Reporting View