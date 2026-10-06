



# Tool Decision Register — Earnings Quality Lens (v0.2, Phase 0A revised)

**Constraint:** supplied CSV is the only data source; nothing is fetched from the internet. The Anthropic API is the only outbound call and supplies language, never data.

Revisited at every gate. Status: **USE** · **PARTIAL** · **SKIP**. Reasons are specific to this project.
Items marked ⏳ depend on answers to the Phase 0A gate questions.

| # | Component | Decision | Project-specific reason |
|---|---|---|---|
| 1 | Analytical thinking | USE | Issue tree on "what makes growth high-quality" drives every later phase |
| 2 | Excel | USE | Finance audiences live in Excel: tie-out workbook + a margin what-if model for one company |
| 3 | SQL | USE | Medallion layers over a 1,750-row panel |
| 4 | Advanced SQL | USE | LAG for YoY, rolling 4-quarter TTM windows, gaps-and-islands for "consecutive quarters of margin expansion", ranking within sector |
| 5 | Query optimisation | USE (LEAN) | Small data; demonstrated on the TTM/rolling queries and on a 10× synthetic scale-up |
| 6 | KPI framework | USE | Dataset-derived margins, growth, operating leverage, R&D/SG&A intensity; many classic finance KPIs tagged Needs data |
| 7 | Power BI | USE ⏳ | Finance stakeholders expect it; requires Windows for Power BI Desktop. Fallback: Streamlit dashboard |
| 8 | Data storytelling | USE | Earnings-season brief for Head of Research |
| 9 | GenAI + prompt engineering | USE | NL Q&A and brief writer |
| 10 | AI with SQL | USE | Text-to-SQL over the governed KPI views; the twist vs the beverage project is **numeric accuracy as a release gate** |
| 11 | AI with Python (enrichment) | SKIP | No text columns and no text corpus under the offline constraint; nothing to enrich. LLM use is limited to Q&A and narrative (#10, #26) |
| 12 | AI + Excel | PARTIAL ⏳ | Depends on Copilot / Python-in-Excel licence; otherwise documented as not available |
| 13 | AI + Power BI | PARTIAL ⏳ | Non-Copilot AI visuals (Key Influencers, Decomposition Tree, anomaly detection) if Power BI is in scope |
| 14 | Automation | USE | No pull from source. File-drop pipeline: a new quarter's CSV lands in `data/raw` → contract check → Bronze → Gold → rescoring → brief. Demonstrated by replaying the withheld latest quarter |
| 15a | AI agent (single) | USE | Analyst assistant choosing between SQL, forecast and document tools |
| 15b | Agentic AI (multi-agent) | PARTIAL | Canonical multi-agent build lives in the beverage project. Here: benchmark single agent; escalate only if evals show a gap |
| 16 | APIs | USE (build) / PARTIAL (consume) | Build FastAPI. Consume only the Anthropic API; no data APIs, by design. Documented as a deliberate constraint |
| 17 | MCP | USE (LEAN) | Read-only server exposing Gold KPIs and forecasts to Claude Desktop / the agent |
| 18 | RAG | PARTIAL (lean) | No external documents. Corpus = the project's own methodology docs (KPI spec cards, dictionary, model cards) so the agent can answer "how is X defined?" with citations. Airline project remains the canonical RAG build |
| 19 | LangGraph | USE | Single agent built in LangGraph after the from-scratch ReAct version |
| 20 | LangChain | PARTIAL | See rule below |
| 21 | LangSmith | USE | Tracing + offline experiments on the golden sets |
| 22 | LLM evals | USE | Numeric accuracy, execution accuracy, faithfulness, abstention, injection tests |
| 23 | LLMOps | USE | Cost/latency logging, caching, guardrails |
| 24 | ML models | USE | Forecasting (hero), clustering of business-model archetypes, anomaly detection |
| 25 | AWS + domain + HTTPS | USE | Requested; EC2 + Docker Compose + Nginx + Certbot |
| 26 | AI-assisted storytelling | USE | Brief writer receives code-computed numbers only; automated fact-check |
| 27 | Semantic layer | USE | Governed KPI views in the Gold layer; consumed by SQL, DAX, API, agent |
| 28a | A/B testing | USE (simulated) | No real experiment exists. Design a test of the "quality-alert" product on analysts; validate the pipeline on a simulated experiment with a known effect |
| 28b | Observational causal inference | PARTIAL | Candidate natural experiment: 2017 US Tax Cuts and Jobs Act → effective tax rate (DiD / synthetic control). Weak control group (2 non-US filers) stated openly |
| 29 | Data contracts, lineage, DQ monitoring | USE | Guards the file-drop path: schema, types, identities, volume checks on any new CSV |
| 30 | Data versioning | USE (LEAN) | Static snapshot: SHA-256 logged in Bronze; new file drops get their own hash |
| 31 | Open-weight vs API | PARTIAL (optional) | Anthropic API is the default. Local model comparison only if you want it (needs a one-time model download) |
| 32 | NIST AI RMF / ISO 42001 | USE (LEAN) | One-page mapping |
| 33 | Model risk management | PARTIAL | Not a regulated-bank model; model card + usage limits + monitoring in MRM spirit |
| 34 | Demo video + portfolio hub | USE | Always |
| 35 | Deep learning (PyTorch) | USE | MLP forecaster with company embeddings as challenger to LightGBM; expected to lose on n=23 — tested, not assumed |
| 36 | Docker | USE | From M1 |
| 37 | Fine-tuning | USE (concepts) / SKIP (hands-on) | No narrow high-volume text task here; hands-on LoRA lives in the standalone repo, linked |

## LangChain decision (Phase 0; restated in Phase 16)
**PARTIAL.** USE: chat-model interface (Anthropic), text splitters and Chroma integration for the lean methodology RAG, `langchain-mcp-adapters` to connect the MCP server to the LangGraph agent. SKIP: `create_agent` and chains for the text-to-SQL path — hand-built LangGraph nodes keep every prompt and SQL step visible, which matters when numeric accuracy is the release gate. Both choices are defensible: fewer abstractions exactly where correctness is audited.