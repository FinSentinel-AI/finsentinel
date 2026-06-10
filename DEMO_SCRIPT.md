# FinSentinel-AI — 3-Minute Demo Script
Google Cloud Rapid Agent Hackathon 2026 — Financial Services + MongoDB Partner Track

---

## [0:00–0:20] Hook — The Problem

**(Show: title slide or empty terminal/UI)**

> "Every day, banks generate thousands of suspicious transactions. Investigating
> just one fraud or money-laundering case — pulling records, cross-referencing
> watchlists, checking regulations, and writing a Suspicious Activity Report —
> takes a compliance analyst up to **three days**.
>
> FinSentinel-AI does it in under **60 seconds**."

---

## [0:20–0:40] Solution Overview

**(Show: architecture diagram or README, then switch to the running UI at localhost:5173)**

> "FinSentinel-AI is a team of 5 autonomous AI agents, powered by **Gemini 2.5
> Flash** and built on **MongoDB Atlas** with vector search. Each agent has a
> specialist role — Fraud Detection, AML Analysis, Risk Scoring, Compliance
> Checking, and SAR Report Generation — and they run as a sequential pipeline,
> streaming results live to the analyst."

---

## [0:40–2:10] Live Demo — The Investigation

**(Show: FinSentinel UI, query box pre-filled)**

> "Here's the FinSentinel dashboard. I'll launch an investigation across the
> last 24 hours of transactions — over **9,449 real records** stored in
> MongoDB Atlas."

**(Click "Launch Investigation")**

> "Watch the agents activate one by one in real time."

**(Narrate as each agent streams its output — pause briefly on each)**

1. **Orchestrator** — "First, the Orchestrator pulls the raw transaction data
   from MongoDB Atlas — no API cost, just a direct query."

2. **Fraud Detector** — "The Fraud Detector flags account ACC-10863 — 15
   transactions in a single day, a clear velocity abuse pattern, fraud
   probability rated High."

3. **AML Analyst** — "Next, the AML Analyst cross-references structuring and
   layering patterns — checking for sub-$10K cash deposits designed to evade
   reporting thresholds, and screening against OFAC watchlists."

4. **Risk Officer** — "The Risk Officer combines both findings into a
   composite risk score and assigns an escalation priority — here, MEDIUM,
   recommending an immediate SAR filing."

5. **Compliance Checker** — "The Compliance Checker maps the findings to real
   regulations — BSA Suspicious Activity Reporting, Currency Transaction
   Reports, and OFAC sanctions requirements."

6. **Report Generator** — "Finally, the Report Generator produces a complete,
   regulator-ready **SAR — FinCEN Form 111** — fully formatted, with subject
   accounts, evidence, and recommended actions."

**(Show the completed investigation, total time ~30-160s)**

> "From raw data to a filed-ready SAR — fully autonomous, end to end."

---

## [2:10–2:40] Technical Architecture

**(Show: architecture diagram / code structure)**

> "Under the hood: a FastAPI backend streams agent events over WebSocket to a
> React frontend. MongoDB Atlas stores transactions, customers, watchlists,
> and compliance rules — with a vector search index enabling semantic
> similarity search across historical fraud cases. Each of the 5 agents makes
> a single Gemini 2.5 Flash call, keeping the pipeline fast and cost-efficient
> — fractions of a cent per investigation."

---

## [2:40–3:00] Close — Impact

**(Show: final SAR report on screen)**

> "FinSentinel-AI turns a 3-day manual compliance workflow into a sub-minute
> automated investigation — giving financial institutions the speed they need
> to catch fraud and meet regulatory deadlines, without adding headcount.
>
> FinSentinel-AI — built with Gemini and MongoDB Atlas. Thank you."

---

## Recording Tips

- Record the UI at 1440x900 or your screen's native resolution for crispness.
- Do a dry run first — investigation timing varies (30s–160s); pick a take
  where it completes briskly.
- Keep narration paced to match agent streaming — don't rush past the visible
  agent outputs, since that's the visual proof of "autonomous."
- Zoom in on the final SAR report text briefly so judges can read the format.
- If using screen recording + voiceover separately, record the UI run first,
  then write narration timestamps to match the actual agent completion times.
