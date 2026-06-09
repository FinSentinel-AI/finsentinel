# FinSentinel — Autonomous Financial Crime Intelligence

**Google Cloud Rapid Agent Hackathon 2026 · Financial Services Track · MongoDB Partner**

> 5 autonomous AI agents that detect fraud, investigate AML violations, and generate regulatory-ready SAR reports in under 60 seconds — replacing a compliance workflow that normally takes 3 days.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini%202.5%20Flash-4285F4)](https://cloud.google.com/vertex-ai)
[![MongoDB Atlas](https://img.shields.io/badge/Partner-MongoDB%20Atlas-00ED64)](https://www.mongodb.com/atlas)
[![Google Cloud](https://img.shields.io/badge/Deployed%20on-Google%20Cloud%20Run-4285F4)](https://cloud.google.com/run)

---

## What It Does

FinSentinel is a multi-agent AI platform for financial crime investigation. When a compliance analyst submits a query, five specialist agents execute in sequence — each with direct access to MongoDB Atlas via the MongoDB MCP server — and produce a complete investigation with a regulatory-ready Suspicious Activity Report (SAR).

**What takes a compliance team 3 days, FinSentinel completes in under 60 seconds.**

---

## Agent Architecture

```
User Query
    │
    ▼
Orchestrator Agent (Gemini 2.5 Flash · Google Cloud Agent Builder)
    │
    ├──► Fraud Detector    — velocity analysis, pattern matching, vector search
    ├──► AML Analyst       — structuring, layering, round-tripping detection
    ├──► Risk Officer      — composite scoring, watchlist cross-reference
    ├──► Compliance Checker — BSA/FINRA/MiFID II/EU AI Act rule matching
    └──► Report Generator  — SAR draft + full audit trail → MongoDB
                                        │
                              MongoDB MCP Server (45+ tools)
                                        │
                              MongoDB Atlas (transactions, customers,
                              watchlists, compliance_rules, audit_log)
```

---

## Partner Integration: MongoDB Atlas MCP

FinSentinel uses the **MongoDB MCP server** (`mongodb-js/mongodb-mcp-server`) as the data backbone for all 5 agents. Every agent operation — reads, aggregations, vector searches, audit log writes — goes through the MCP server.

Key MongoDB operations used:
| Operation | Agent | Purpose |
|---|---|---|
| `find` | All agents | Retrieve transactions, customers, watchlists |
| `aggregate` | Fraud Detector, AML Analyst | Velocity counts, network graph, structuring detection |
| `aggregate` + `$vectorSearch` | Fraud Detector | Semantic similarity against historical fraud cases |
| `find` + watchlist lookup | Risk Officer | OFAC SDN, PEP, internal blacklist cross-reference |
| `insert-many` | Report Generator | Write SAR draft + full audit trail |
| `update-many` | Report Generator | Flag transactions as `under_review` |

---

## Fraud Scenarios Detected

| Scenario | Detection Method | Regulatory Trigger |
|---|---|---|
| Velocity abuse | >5 txns/hour per account | SAR if >$5,000 total |
| Structuring (smurfing) | Multiple deposits just below $10K | CTR + SAR mandatory |
| Round-tripping | Circular network graph detection | SAR + enhanced due diligence |
| Layering | 3+ hop transaction chains | SAR + FINRA 3310 |
| High-risk jurisdiction | FATF country code matching | OFAC report + SAR |
| Watchlist match | OFAC SDN / PEP cross-reference | Immediate block + report |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | Google ADK (Agent Development Kit) |
| Agent Model | Gemini 2.5 Flash |
| Agent Runtime | Google Cloud Agent Builder / Vertex AI Agent Engine |
| Partner MCP | MongoDB Atlas MCP (`mongodb-js/mongodb-mcp-server`) |
| Database | MongoDB Atlas M0 (free tier) |
| Backend | FastAPI + WebSocket (Python 3.12) |
| Frontend | React 18 + TypeScript + Vite |
| Deployment | Google Cloud Run |
| CI | GitHub Actions |

---

## Compliance Coverage

- **BSA**: CTR (>$10K cash), SAR (>$5K suspicious) — auto-detected and filed
- **FINRA Rule 3310**: AML program flag for annual testing
- **MiFID II Article 26**: T+1 transaction reporting flag
- **EU AI Act (High-Risk)**: Human oversight logs for every autonomous decision
- **GDPR Article 22**: Decision lineage and right-to-explanation in every SAR
- **OFAC SDN**: Real-time watchlist matching

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/FinSentinel-AI/finsentinel
cd finsentinel

# 2. Environment
cp .env.example .env
# Edit .env with your MongoDB URI and GCP project ID

# 3. Install
make install

# 4. Seed database (10,000 synthetic transactions + fraud scenarios)
make seed

# 5. Run locally
make dev
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

---

## Deployment

```bash
# Deploy to Google Cloud Run (one command)
make deploy PROJECT_ID=your-gcp-project-id MONGODB_URI=your-uri
```

---

## Team

| Member | GitHub | Role |
|---|---|---|
| **Emmanuel Adutwum** ⭐ | `emmanuelsoneuclid10` | **Senior Lead Developer & Principal Architect** — multi-agent ADK orchestration, MongoDB MCP integration, fraud/AML detection algorithms, FastAPI backend, CI/CD, full system design |
| **Shiv Kumar Mishra** | `shivkumarmishra718` | **Distributed Systems Engineer** — agent coordination protocols, data pipeline design, risk scoring engine |
| **Lekha Saradhi** | `lekhakuncham` | **Frontend & Compliance Engineer** — React dashboard, investigation flow visualizer, compliance rule mapping |

---

*Google Cloud Rapid Agent Hackathon 2026 · Built with Gemini + MongoDB Atlas + Google Cloud*
