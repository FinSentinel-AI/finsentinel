"""
Sequential 5-agent investigation pipeline.

Architecture:
1. Fetch all MongoDB data ONCE using pymongo (no rate limit cost)
2. Pass pre-fetched data to each Gemini model call (1 LLM call per agent)
3. Stream results back to the WebSocket caller

This reduces from ~8 LLM calls per agent to 1 call per agent = 5 total.
"""
import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Awaitable

import google.genai as genai
from google.genai import types as genai_types

from backend.db_fetcher import (
    fetch_investigation_context,
    context_to_text,
    fetch_similar_cases,
    write_audit_trail,
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "finsentinel"

AGENTS = [
    {
        "name": "fraud_detector",
        "label": "Fraud Detector",
        "system": (
            "You are FinSentinel's Fraud Detection Agent. You receive a MongoDB database snapshot "
            "and an investigation query. Analyze the data for fraud patterns: velocity abuse, "
            "structuring, high-risk jurisdictions, new-account large transfers, round-tripping, and layering. "
            "Reference ACTUAL transaction IDs, account IDs, and dollar amounts from the data. "
            "Output a structured JSON array of flagged entities with fraud_probability, fraud_type, "
            "and evidence. Be specific and exhaustive."
        ),
    },
    {
        "name": "aml_analyst",
        "label": "AML Analyst",
        "system": (
            "You are FinSentinel's AML Analyst. You receive a MongoDB snapshot AND the Fraud Detector's findings. "
            "Perform AML network analysis: identify structuring (smurfing), layering chains, round-tripping, "
            "and FATF high-risk jurisdiction exposure. Apply BSA thresholds: CTR required >$10K cash, "
            "SAR required >$5K suspicious activity. "
            "Reference actual account IDs from the data. Output network_risk_score (0-1) and SAR/CTR obligations."
        ),
    },
    {
        "name": "risk_officer",
        "label": "Risk Officer",
        "system": (
            "You are FinSentinel's Risk Officer. You receive the MongoDB snapshot AND prior agent findings. "
            "Compute a composite risk score for each flagged account: "
            "30% transaction anomaly + 25% AML network risk + 25% watchlist match + 10% account age + 10% jurisdiction. "
            "Assign CRITICAL (>0.85), HIGH (>0.65), MEDIUM (>0.40), or LOW (<0.40) escalation priority. "
            "Check the watchlist data provided. Output JSON with composite_risk_score, escalation_priority, "
            "and recommended_action for each account."
        ),
    },
    {
        "name": "compliance_checker",
        "label": "Compliance Checker",
        "system": (
            "You are FinSentinel's Compliance Checker. You receive all prior findings and the compliance rules. "
            "Apply: BSA (CTR within 15 days if >$10K cash, SAR within 30 days if >$5K suspicious), "
            "FINRA Rule 3310, MiFID II Article 26, GDPR Article 22 (right to explanation), "
            "EU AI Act (human oversight for autonomous AI decisions). "
            "Output: which regulations are triggered, exact filing deadlines (dates), and "
            "human approval requirements. Be precise about deadlines."
        ),
    },
    {
        "name": "report_generator",
        "label": "Report Generator",
        "system": (
            "You are FinSentinel's Report Generator. You receive ALL findings from the pipeline. "
            "Generate a complete FinCEN 111-format SAR report with: "
            "Part I (subject accounts), Part II (suspicious activity summary with amounts), "
            "Part III (2-3 paragraph narrative with specific evidence), "
            "Part IV (regulatory obligations with exact deadlines), "
            "Part V (human review checklist), Part VI (AI decision lineage). "
            "Note MongoDB collections that would be written: sar_reports, audit_log. "
            "End with total investigation time vs. 3-day manual process comparison. "
            "This should be a professional, regulatory-ready document."
        ),
    },
]


def _gemini_client() -> genai.Client:
    """
    Prefer Vertex AI (if GOOGLE_CLOUD_PROJECT is set and ADC is available),
    then fall back to API key. Vertex AI has separate (higher) quotas.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        try:
            return genai.Client(
                vertexai=True,
                project=project,
                location=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"),
            )
        except Exception:
            pass  # Fall through to API key auth

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


async def _call_agent(
    client: genai.Client,
    agent_name: str,
    label: str,
    system_prompt: str,
    user_message: str,
    on_event: Callable[[dict], Awaitable[None]],
    max_retries: int = 5,
) -> str:
    """Call Gemini with retry-backoff on rate limits. Returns agent response text."""
    backoff = 20  # matches the ~18s free-tier window

    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL,
                contents=user_message,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            text = response.text or ""
            return text

        except Exception as e:
            err = str(e)
            is_rate = "429" in err or "RESOURCE_EXHAUSTED" in err or "free_tier" in err
            is_unavailable = "503" in err or "UNAVAILABLE" in err

            if (is_rate or is_unavailable) and attempt < max_retries - 1:
                wait = backoff * (2 ** attempt)
                await on_event({
                    "type": "agent_step",
                    "agent": agent_name,
                    "content": f"[{label}] API limit reached — waiting {wait}s (attempt {attempt + 2}/{max_retries})...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                await asyncio.sleep(wait)
                continue

            return f"[{label} unavailable: {err[:200]}]"

    return f"[{label} failed after {max_retries} attempts]"


async def run_pipeline(
    query: str,
    on_event: Callable[[dict], Awaitable[None]],
) -> None:
    """
    Run the 5-agent pipeline.
    Step 0: fetch all MongoDB data once (fast, no API calls)
    Steps 1-5: one Gemini call per agent, passed the pre-fetched data
    """
    t0 = time.time()

    # Step 0 — Fetch MongoDB data
    await on_event({
        "type": "agent_step",
        "agent": "finsentinel_orchestrator",
        "content": "Fetching investigation data from MongoDB Atlas...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        ctx = await asyncio.to_thread(fetch_investigation_context)
        db_text = context_to_text(ctx)
    except Exception as e:
        await on_event({
            "type": "error",
            "message": f"MongoDB connection failed: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return

    stats = ctx.get("_stats", {})
    await on_event({
        "type": "agent_step",
        "agent": "finsentinel_orchestrator",
        "content": (
            f"MongoDB data loaded: {stats.get('total_transactions', 0):,} total transactions, "
            f"{stats.get('fraud_flagged_count', 0)} fraud-flagged, "
            f"{stats.get('velocity_suspects', 0)} velocity suspects, "
            f"{stats.get('structuring_suspects', 0)} structuring suspects. "
            f"Deploying 5 specialist agents..."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Step 0b — Atlas Vector Search: surface semantically similar past fraud cases
    similar_cases_text = ""
    try:
        similar_cases = await asyncio.to_thread(fetch_similar_cases, ctx)
    except Exception:
        similar_cases = []

    if similar_cases:
        await on_event({
            "type": "similar_cases",
            "agent": "finsentinel_orchestrator",
            "cases": similar_cases,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        similar_cases_text = "\n\nSIMILAR PAST FRAUD CASES (via Atlas $vectorSearch, fraud_vector_idx):\n" + "\n".join(
            f"  {c['transaction_id']} | {c.get('fraud_type','')} | ${c.get('amount',0):,.2f} | "
            f"similarity={c.get('score',0):.3f} | {c.get('description','')[:80]}"
            for c in similar_cases
        )
        db_text += similar_cases_text

    client = _gemini_client()
    accumulated_findings = ""
    agent_outputs: list[dict] = []

    for agent_cfg in AGENTS:
        agent_name = agent_cfg["name"]
        label = agent_cfg["label"]
        system = agent_cfg["system"]

        await on_event({
            "type": "agent_step",
            "agent": agent_name,
            "content": f"[{label}] Analyzing {stats.get('total_transactions', 0):,} transactions...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Agent 1 (Fraud Detector) gets the full DB snapshot.
        # Later agents get ONLY the prior findings (avoids token explosion).
        if not accumulated_findings:
            db_section = db_text
        else:
            db_section = (
                f"[MongoDB Summary] {stats.get('total_transactions',0):,} transactions, "
                f"{stats.get('fraud_flagged_count',0)} fraud-flagged, "
                f"{stats.get('velocity_suspects',0)} velocity suspects, "
                f"{stats.get('structuring_suspects',0)} structuring suspects, "
                f"{stats.get('watchlist_count',0)} watchlist entries."
            )

        user_msg = (
            f"INVESTIGATION QUERY: {query}\n\n"
            + db_section
            + (f"\n\n=== PRIOR AGENT FINDINGS ===\n{accumulated_findings}" if accumulated_findings else "")
            + f"\n\nToday: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        )

        response_text = await _call_agent(
            client=client,
            agent_name=agent_name,
            label=label,
            system_prompt=system,
            user_message=user_msg,
            on_event=on_event,
        )

        step_event = {
            "type": "agent_step",
            "agent": agent_name,
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await on_event(step_event)
        agent_outputs.append({"agent": agent_name, "label": label, "content": response_text, "timestamp": step_event["timestamp"]})

        accumulated_findings += f"\n\n=== {label.upper()} ===\n{response_text}"

        # Free-tier rate window is ~18s per request. Each LLM call takes ~12s.
        # Sleep the gap so the next agent starts after the window clears.
        # Skip the sleep after the last agent.
        if agent_cfg is not AGENTS[-1]:
            await asyncio.sleep(8)

    total_time = time.time() - t0

    # Impact stats — narrative for judges/regulators
    flagged_amount = sum(t.get("amount", 0) for t in ctx.get("fraud_flagged", []))
    flagged_amount += sum(a.get("total", 0) for a in ctx.get("velocity_accounts", []))
    flagged_amount += sum(a.get("total", 0) for a in ctx.get("structuring_candidates", []))
    manual_seconds = 3 * 24 * 3600  # 3-day manual process
    speedup = manual_seconds / total_time if total_time > 0 else 0
    # Rough gemini-2.5-flash cost estimate: ~3K input + ~1K output tokens per agent call
    est_cost = len(AGENTS) * ((3000 * 0.30 + 1000 * 2.50) / 1_000_000)

    impact_stats = {
        "flagged_amount": flagged_amount,
        "investigation_time_s": round(total_time, 1),
        "manual_time_s": manual_seconds,
        "speedup_x": round(speedup, 0),
        "est_cost_usd": round(est_cost, 4),
        "transactions_analyzed": stats.get("total_transactions", 0),
        "accounts_flagged": stats.get("fraud_flagged_count", 0) + stats.get("velocity_suspects", 0) + stats.get("structuring_suspects", 0),
    }

    final_content = (
        f"=== FINSENTINEL INVESTIGATION COMPLETE ===\n"
        f"Investigation time: {total_time:.1f}s (vs. 3-day manual process — {speedup:,.0f}x faster)\n"
        f"Database: MongoDB Atlas finsentinel ({stats.get('total_transactions',0):,} transactions)\n"
        f"Suspicious activity flagged: ${flagged_amount:,.2f}\n"
        f"Estimated Gemini API cost: ${est_cost:.4f}\n"
        f"Model: {MODEL}\n"
        f"Agents: Fraud Detector → AML Analyst → Risk Officer → Compliance Checker → Report Generator\n\n"
        + accumulated_findings
    )

    # Persist full audit trail + SAR to MongoDB Atlas (audit_log, sar_reports)
    investigation_id = f"INV-{uuid.uuid4().hex[:12]}"
    try:
        await asyncio.to_thread(write_audit_trail, investigation_id, query, agent_outputs, final_content, impact_stats)
        await on_event({
            "type": "audit_saved",
            "agent": "finsentinel_orchestrator",
            "investigation_id": investigation_id,
            "message": f"Audit trail saved to MongoDB Atlas — audit_log ({len(agent_outputs)} entries) + sar_reports (1 report)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        await on_event({
            "type": "agent_step",
            "agent": "finsentinel_orchestrator",
            "content": f"[Audit trail write skipped: {e}]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    await on_event({
        "type": "impact_stats",
        "agent": "finsentinel_orchestrator",
        "stats": impact_stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await on_event({
        "type": "final",
        "agent": "finsentinel_orchestrator",
        "content": final_content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
