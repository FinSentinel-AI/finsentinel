# FinSentinel — Autonomous Financial Crime Intelligence

**Google Cloud Rapid Agent Hackathon 2026 · Financial Services Track · MongoDB Partner**

> 5 autonomous AI agents that detect fraud, investigate AML violations, and generate regulatory-ready SAR reports in under 60 seconds — replacing a compliance workflow that normally takes 3 days.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini%202.5%20Flash-4285F4)](https://cloud.google.com/vertex-ai)
[![MongoDB Atlas](https://img.shields.io/badge/Partner-MongoDB%20Atlas-00ED64)](https://www.mongodb.com/atlas)
[![Google Cloud](https://img.shields.io/badge/Deployed%20on-Google%20Cloud%20Run-4285F4)](https://cloud.google.com/run)

---

## What It Does

FinSentinel is a multi-agent AI platform for financial crime investigation. When a compliance analyst submits a query, five specialist AI agents execute in sequence with real-time access to **MongoDB Atlas** — producing a complete investigation with a regulatory-ready Suspicious Activity Report (SAR).

**What takes a compliance team 3 days, FinSentinel completes in under 60 seconds.**

### Live Investigation Results (from real MongoDB Atlas data)

```
MongoDB Atlas: 9,449 transactions loaded
FRAUD DETECTED:
  ACC-10863: 16 velocity-abuse transactions, $18,420.14 in 24h (fraud_probability=0.95)
  ACC-11148: 13 structured cash deposits, $120,132.48 total (just below $10K each)
  ACC-83372: $496,422 wire transfers across 7 accounts
AML NETWORK: OFAC SDN match identified, >$900K suspicious activity
REGULATIONS TRIGGERED: BSA SAR (30-day deadline), BSA CTR, OFAC report
```

---

## Agent Architecture

```
User Query
    │
    ▼
Step 0: MongoDB Atlas Data Fetch (pymongo · direct · all collections in one shot)
    │
    ├── 9,449 transactions · 49 fraud-flagged · velocity suspects · structuring
    ├── watchlists (OFAC SDN, PEP) · customers · compliance_rules
    └── money-flow network graph
    │
    ▼
Sequential 5-Agent Pipeline (Google ADK + Gemini 2.5 Flash)
    │
    ├──► Agent 1: Fraud Detector
    │         └── Velocity analysis, structuring detection, jurisdiction risk
    │
    ├──► Agent 2: AML Analyst
    │         └── Network graphs, layering chains, BSA SAR/CTR obligations
    │
    ├──► Agent 3: Risk Officer
    │         └── Composite risk scores, watchlist cross-reference, OFAC match
    │
    ├──► Agent 4: Compliance Checker
    │         └── BSA/FINRA/MiFID II/EU AI Act deadlines, human approval rules
    │
    └──► Agent 5: Report Generator
              └── FinCEN 111-format SAR → MongoDB sar_reports + audit_log
    │
    ▼
WebSocket Streaming → React Frontend (real-time investigation flow)
```

---

## Partner Integration: MongoDB Atlas

FinSentinel uses **MongoDB Atlas** as the operational backbone with two integration paths:

### 1. MongoDB MCP Server (Google ADK Integration)
The `mongodb-js/mongodb-mcp-server` provides 25+ tools to ADK agents via stdio MCP protocol. Each agent can call `find`, `aggregate`, `insert-many`, and `update-many` directly on the Atlas cluster.

### 2. Atlas Vector Search (Semantic Fraud Detection)
A 3072-dimensional vector search index (`fraud_vector_idx`) on `transactions.embedding` uses `text-embedding-gemini-2` to find semantically similar historical fraud patterns — catching novel fraud variants that rule-based systems miss.

### MongoDB Collections
| Collection | Purpose |
|---|---|
| `transactions` | 9,449 transactions with fraud flags, embeddings, jurisdiction codes |
| `customers` | Account profiles, risk levels, PEP flags, onboarding dates |
| `watchlists` | OFAC SDN, PEP, internal blacklists |
| `compliance_rules` | BSA/FINRA/MiFID II rules with thresholds and deadlines |
| `sar_reports` | Generated SAR documents (written by Report Generator) |
| `audit_log` | Complete AI decision audit trail (EU AI Act Article 13) |

### MongoDB Operations Used
| Operation | Purpose |
|---|---|
| `find` with filter | Fraud-flagged transactions, watchlist lookup, customer profiles |
| `aggregate` with `$group` | Velocity counts, structuring totals, network graphs |
| `aggregate` with `$lookup` | 3-hop layering detection chains |
| `aggregate` + `$vectorSearch` | Semantic similarity to known fraud patterns (3072-dim cosine) |
| `insert-many` | Write SAR reports and audit trail to Atlas |
| `update-many` | Flag transactions as `under_review` |

---

## Fraud Scenarios Detected

| Scenario | Detection Method | Regulatory Trigger |
|---|---|---|
| Velocity abuse | >5 txns/24h per account | SAR if >$5,000 total |
| Structuring (smurfing) | Multiple deposits just below $10K | CTR + SAR mandatory |
| Round-tripping | Circular network graph detection | SAR + enhanced due diligence |
| Layering | 3+ hop transaction chains | SAR + FINRA 3310 |
| High-risk jurisdiction | FATF country code (IR/KP/SY/CU/SD) | OFAC report + SAR |
| New account large transfer | <30 days old + >$10K transfer | SAR + EDD |
| Watchlist match | OFAC SDN / PEP cross-reference | Immediate block + report |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | Google ADK 2.2.0 (Agent Development Kit) |
| Agent Model | Gemini 2.5 Flash / Gemini 2.5 Flash-Lite |
| Data Integration | MongoDB Atlas MCP (`mongodb-js/mongodb-mcp-server` v1.12.0) |
| Vector Search | Atlas Vector Search (3072-dim, `text-embedding-gemini-2`) |
| Database | MongoDB Atlas M0 (9,449 transactions, 6 collections) |
| Backend | FastAPI + WebSocket streaming (Python 3.13) |
| Frontend | React 18 + TypeScript + Vite |
| Deployment | Google Cloud Run |
| CI | GitHub Actions |

---

## Compliance Coverage

- **BSA**: CTR (>$10K cash), SAR (>$5K suspicious) — auto-detected with exact deadlines
- **FINRA Rule 3310**: AML program flag for annual testing
- **MiFID II Article 26**: T+1 transaction reporting flag
- **EU AI Act (High-Risk)**: Human oversight logs for every autonomous decision
- **GDPR Article 22**: Decision lineage and right-to-explanation in every SAR
- **OFAC SDN**: Real-time watchlist matching with immediate escalation

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/FinSentinel-AI/finsentinel
cd finsentinel

# 2. Environment
cp .env.example .env
# Required variables:
# MONGODB_URI=mongodb+srv://...
# GOOGLE_API_KEY=your-gemini-api-key (with billing enabled)
# GEMINI_MODEL=gemini-2.5-flash

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install frontend dependencies
cd frontend && npm install && cd ..

# 5. Seed MongoDB with synthetic fraud data + embeddings
python3 -m backend.seed_data

# 6. Run backend
uvicorn backend.main:app --port 8000

# 7. Run frontend (new terminal)
cd frontend && npm run dev
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```

---

## API Keys Required

1. **MongoDB Atlas**: Free M0 cluster at https://cloud.mongodb.com
2. **Google AI Studio**: API key at https://aistudio.google.com/apikey
   - Enable billing for full quota (required for 5-agent pipeline)
   - Free tier: ~1,000 RPD for Gemini 2.5 Flash-Lite

---

## Deployment

```bash
# Deploy to Google Cloud Run
make deploy PROJECT_ID=your-gcp-project-id MONGODB_URI=your-uri
```

---

## Team

| Member | Role |
|---|---|
| **Emmanuel Adutwum** | Lead Developer & Principal Architect — multi-agent ADK orchestration, MongoDB MCP integration, fraud/AML detection algorithms, FastAPI backend, full system design |
| **Shiv Kumar Mishra** ([@shivkumarmishra718](https://github.com/shivkumarmishra718)) | Contributor |
| **Lekha Saradhi** ([@lekhakuncham](https://github.com/lekhakuncham)) | Contributor |

---

*Google Cloud Rapid Agent Hackathon 2026 · Built with Gemini + MongoDB Atlas + Google ADK*
