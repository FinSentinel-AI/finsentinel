# Devpost Submission — FinSentinel-AI

Copy/paste each section into the corresponding Devpost field.

---

## Project Name
FinSentinel — Autonomous Financial Crime Intelligence

## Tagline / Elevator Pitch
5 autonomous Gemini agents turn a 3-day AML/fraud investigation into a sub-3-minute, regulator-ready SAR — powered by MongoDB Atlas vector search.

## Links
- **Repo**: https://github.com/FinSentinel-AI/finsentinel
- **Demo video**: demo/finsentinel_demo.mp4 (upload directly to Devpost, or to YouTube/Vimeo and link)
- **Live demo**: http://localhost:5173 (or your Cloud Run URL if deployed)

---

## What it does

FinSentinel is a multi-agent AI platform for financial crime investigation. A compliance analyst submits a natural-language query (e.g. "Investigate the last 24 hours of transactions for fraud and AML violations"), and five specialist Gemini 2.5 Flash agents run in sequence — Fraud Detector → AML Analyst → Risk Officer → Compliance Checker → Report Generator — streaming live findings to a React dashboard.

Along the way:
- A MongoDB Atlas **`$vectorSearch`** query (gemini-embedding-2, 3072-dim, cosine) surfaces semantically similar past fraud cases from the historical transaction corpus, giving every agent — and the analyst — instant precedent.
- The full chain-of-reasoning from all 5 agents, plus the final SAR, is written back to MongoDB Atlas (`audit_log` + `sar_reports` collections) as a regulator-facing AI decision-lineage audit trail — directly addressing GDPR Art. 22 and EU AI Act human-oversight requirements.
- The pipeline produces a complete FinCEN Form 111 Suspicious Activity Report with subject accounts, evidence, regulatory deadlines (BSA/FINRA/MiFID II), and a human-review checklist.
- A live "impact strip" shows the dollar amount flagged, total investigation time vs. the 3-day manual baseline (~1,500x speedup), transactions analyzed, and the actual Gemini API cost (~$0.017/run).

What normally takes a compliance team **3 days** of manual record-pulling, watchlist cross-referencing, and report-writing, FinSentinel completes **end-to-end in under 3 minutes** for less than two cents in API costs.

---

## How we built it

- **Backend**: FastAPI + WebSocket streaming (`/ws/investigate`). `backend/db_fetcher.py` pre-fetches all required MongoDB Atlas data (transactions, customers, watchlists, compliance rules, money-flow network) in a single batch via pymongo — zero per-agent tool-call overhead. `backend/pipeline.py` then runs each of the 5 agents as one Gemini 2.5 Flash call, passing forward the accumulated findings.
- **MongoDB Atlas**: 9,449-document transaction corpus seeded with realistic fraud patterns (velocity abuse, structuring, round-tripping, OFAC SDN matches). A vector search index (`fraud_vector_idx`, 3072-dim cosine over gemini-embedding-2 embeddings) enables `$vectorSearch` for similar-case retrieval. `audit_log` and `sar_reports` collections persist every investigation's full reasoning chain.
- **Gemini 2.5 Flash** via `google.genai`, with exponential backoff for free-tier rate limits, generates each agent's structured analysis (fraud probabilities, AML risk scores, composite risk, regulatory obligations, and the final SAR narrative).
- **Frontend**: React + Vite, with a 5-step pipeline progress visualization (`InvestigationFlow`), live agent event log, similar-cases panel, impact stats strip, and a downloadable SAR report component.

---

## Challenges we ran into

- Tuning the 5-agent pipeline to stay within Gemini free-tier rate limits while keeping end-to-end latency under 3 minutes (solved with a single-call-per-agent architecture and adaptive backoff).
- Wiring `$vectorSearch` correctly against a 3072-dim embedding index and surfacing it as a live, judge-visible "similar past cases" feature rather than just a backend detail.
- Designing an audit trail schema that satisfies real regulatory requirements (GDPR Art. 22 right-to-explanation, EU AI Act human oversight) without slowing down the pipeline.

---

## Accomplishments we're proud of

- A fully working, end-to-end autonomous investigation — from raw MongoDB data to a regulator-ready FinCEN Form 111 SAR — with zero human intervention, in under 3 minutes.
- Real MongoDB Atlas vector search powering a genuinely useful "similar fraud cases" feature, not a bolt-on demo.
- A persistent, queryable AI audit trail that turns "black box" agent reasoning into a regulator-facing artifact.
- Live impact metrics (cost, time, $ flagged) that make the ROI case immediately obvious to a judge or a compliance executive.

---

## What's next for FinSentinel

- Multi-case batch investigations and a case-management queue.
- Fine-tuned risk-scoring model trained on the audit_log corpus.
- Real-time streaming ingestion from a live transaction feed instead of a static MongoDB snapshot.
- Deployment to Google Cloud Run with Vertex AI for production-scale quota.

---

## Built With
gemini-2.5-flash, gemini-embedding-2, google-genai, mongodb-atlas, mongodb-vector-search, pymongo, fastapi, websockets, react, vite, typescript, python

---

## Team
Emmanuel Adutwum — Lead Developer & Principal Architect (solo)
