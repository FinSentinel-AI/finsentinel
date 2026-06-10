# FinSentinel — Autonomous Financial Crime Intelligence Platform

**What it is:** A full-stack, production-deployed multi-agent AI system that automates financial fraud and AML (anti-money-laundering) investigations. Built solo for the Google Cloud Rapid Agent Hackathon 2026 (Financial Services + MongoDB Partner track).

**Live URL:** https://finsentinel-426594889902.us-central1.run.app
**Repo:** https://github.com/FinSentinel-AI/finsentinel (MIT licensed)

## The Problem It Solves
Compliance analysts at financial institutions manually investigate suspicious transactions — pulling records, cross-referencing sanctions watchlists, checking applicable regulations (BSA, FINRA, MiFID II, OFAC), and drafting a formal Suspicious Activity Report (SAR, FinCEN Form 111). This typically takes ~3 days per case. FinSentinel automates the entire workflow end-to-end in under 3 minutes for less than $0.02 in API cost.

## Architecture — Sequential 5-Agent Pipeline

A compliance analyst submits a natural-language query (e.g., "Investigate the last 24 hours of transactions for fraud and AML violations. Generate a SAR if needed.") and five specialist AI agents run in sequence, each receiving the accumulated findings of the previous agents:

1. **Fraud Detector** (`agent/agents/fraud_detector.py`) — analyzes transaction patterns for velocity abuse, structuring, round-tripping; outputs flagged entities with fraud probabilities.
2. **AML Analyst** (`agent/agents/aml_analyst.py`) — cross-references OFAC SDN sanctions lists, analyzes the money-flow network for layering/structuring, produces an AML risk report.
3. **Risk Officer** (`agent/agents/risk_officer.py`) — combines fraud + AML signals into a composite risk score per account/entity.
4. **Compliance Checker** (`agent/agents/compliance_checker.py`) — maps findings to specific regulatory obligations (BSA SAR 30-day filing deadline, BSA CTR, OFAC reporting, FINRA/MiFID II requirements).
5. **Report Generator** (`agent/agents/report_generator.py`) — synthesizes everything into a complete FinCEN Form 111 SAR: subject accounts, supporting evidence, regulatory deadlines, and a human-review checklist.

Each agent is a single call to **Gemini 2.5 Flash** via the `google.genai` SDK, with adaptive exponential backoff to handle free-tier rate limits — this single-call-per-agent architecture was a deliberate design choice to keep latency under 3 minutes and cost under 2 cents per run.

## Backend (`backend/`)

- **FastAPI** application (`backend/main.py`, 108 lines) exposing a `/ws/investigate` WebSocket endpoint that streams live agent events to the frontend in real time (status updates, per-agent reasoning, similar-case results, audit confirmation, impact stats, final report).
- **`backend/db_fetcher.py`** (303 lines) — pre-fetches *all* required data from MongoDB Atlas (transactions, customers, watchlists, compliance rules, money-flow network) in a single batch via `pymongo` *before* the agent pipeline starts. This eliminates per-agent tool-call/round-trip overhead, which was critical for staying within the latency budget.
  - `fetch_similar_cases()` — runs a MongoDB Atlas `$vectorSearch` query (3072-dim, cosine similarity, `gemini-embedding-2` embeddings) against a `fraud_vector_idx` index to surface semantically similar historical fraud cases, streamed to the UI as a "Similar Past Cases" panel.
  - `write_audit_trail()` — persists the full reasoning chain of all 5 agents plus the final SAR to MongoDB (`audit_log` and `sar_reports` collections), keyed by a generated `investigation_id` (e.g., `INV-4f0da7a0da04`) — designed as a regulator-facing AI decision-lineage audit trail addressing GDPR Article 22 (right to explanation) and EU AI Act human-oversight requirements.
- **`backend/pipeline.py`** (355 lines) — orchestrates the 5-agent sequence, accumulates context between agents, computes "impact stats" (dollar amount flagged, investigation time vs. 3-day manual baseline, ~1,500-1,700x speedup multiplier, estimated Gemini API cost, transactions analyzed).
- **`backend/seed_data.py`** (367 lines) — seeds MongoDB Atlas with a realistic synthetic dataset: **9,449 transaction documents** including embedded fraud patterns (velocity abuse, structuring/smurfing with sub-$10K cash deposits, round-tripping, OFAC SDN sanctions matches).

## Database — MongoDB Atlas

- Cluster: M0 tier, MongoDB 8.0
- Collections: `transactions` (9,449 docs), `customers`, `watchlists`, `compliance_rules`, `sar_reports`, `audit_log`
- Vector Search index `fraud_vector_idx`: 3072-dimension, cosine similarity, built on `gemini-embedding-2` embeddings — used for the similar-case retrieval feature
- This is the "MongoDB Partner" track differentiator: vector search isn't a bolt-on demo, it's wired directly into the live agent pipeline as a decision-support signal

## Frontend (`frontend/src/`)

- **React + Vite + TypeScript**
- `App.tsx` (295 lines) — main dashboard: query input with 4 preset investigation scenarios, WebSocket client connecting to the backend, live agent event log with color-coded agent badges, elapsed-time timer
- `components/InvestigationFlow.tsx` — 5-step pipeline progress visualization showing which agent is currently active/completed
- `components/SARReport.tsx` — renders the final downloadable SAR report
- Impact stats strip showing real-time metrics: `$X flagged`, `Xs vs 3 days (1,XXXx faster)`, `X transactions analyzed`, `~$0.0XXX Gemini API cost`
- "Saved to MongoDB Atlas (INV-xxxx)" badge confirming the audit trail write

## Deployment & Infrastructure

- **Containerized with Docker** — single container serves both the FastAPI backend and the built React frontend (static files)
- **Deployed to Google Cloud Run** (project `gen-lang-client-0856177200`, region `us-central1`)
- Built via **Google Cloud Build** (`gcloud builds submit --tag gcr.io/.../finsentinel:latest`)
- Environment configuration via `--env-vars-file` (MongoDB URI, Gemini API key, model config) — deliberately configured to use Gemini API-key auth rather than Vertex AI service-account auth
- Solved a Cloud Run gotcha: default health-check port is 8080, but the container listens on 8000 — fixed via explicit `--port=8000`
- Solved a production bug: WebSocket connections were hardcoded to `ws://`, which browsers block as "mixed content" on an HTTPS-served page (Cloud Run serves HTTPS) — fixed by dynamically selecting `wss://` vs `ws://` based on `window.location.protocol`

## Demo & Results

- Recorded a ~161-second narrated demo video (Playwright headless browser automation + macOS `say` text-to-speech narration, muxed with ffmpeg) showing a full live investigation run
- **Verified live results**: a real run against the production deployment completed in 152.9 seconds, flagged $2,165,962.52 in suspicious activity across accounts (ACC-10863 — velocity abuse, 16 transactions, $18,420.14; ACC-11148 — structuring via 13 sub-$10K cash deposits totaling $120,132.48; ACC-83372 — $496,422 across 7 wire transfers with an OFAC SDN match), generated a complete FinCEN Form 111 SAR, and wrote a full audit trail to MongoDB — all for ~$0.017 in Gemini API cost.

## Architecture Note: ADK Orchestrator vs. Sequential Pipeline

The repo contains two agent implementations:

- **`agent/orchestrator.py`** — an earlier design using Google's **Agent Development Kit (ADK)** (`google.adk.agents.Agent`), with an MCP (Model Context Protocol) toolset connecting to MongoDB via `MCPToolset`/`StdioConnectionParams`. This defines a `root_agent` built by `create_orchestrator()`.
- **`backend/pipeline.py`** — the **current production path**, a hand-rolled sequential pipeline using direct `google.genai` SDK calls (one Gemini 2.5 Flash call per agent) plus `backend/db_fetcher.py` for direct `pymongo` data access.

**`backend/main.py` only imports and calls `run_pipeline` from `backend/pipeline.py`** — the ADK orchestrator (`agent/orchestrator.py`, `root_agent`) is not imported anywhere in `backend/`. It's effectively dead code / a legacy prototype left over from an earlier architecture iteration, before the switch to the data-first, single-call-per-agent design (made specifically to control latency and stay within Gemini free-tier rate limits, as noted in `pipeline.py`'s own docstring).

## Skills/Technologies Demonstrated

Multi-agent LLM orchestration · Gemini 2.5 Flash (`google.genai` SDK) · prompt engineering for structured agent outputs · MongoDB Atlas (including `$vectorSearch` / vector embeddings) · FastAPI · WebSocket real-time streaming · React/Vite/TypeScript · Docker containerization · Google Cloud Build & Cloud Run deployment · CI/CD debugging (port mismatches, mixed-content/WSS issues) · regulatory domain modeling (BSA, FINRA, MiFID II, OFAC, GDPR, EU AI Act) · cost/latency optimization for production LLM pipelines · end-to-end ownership (architecture → backend → frontend → deployment → demo video → hackathon submission)
