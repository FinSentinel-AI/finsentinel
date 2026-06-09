import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

from agent.agents.fraud_detector import FRAUD_DETECTOR_PROMPT
from agent.agents.aml_analyst import AML_ANALYST_PROMPT
from agent.agents.risk_officer import RISK_OFFICER_PROMPT
from agent.agents.compliance_checker import COMPLIANCE_CHECKER_PROMPT
from agent.agents.report_generator import REPORT_GENERATOR_PROMPT

ORCHESTRATOR_PROMPT = """
You are FinSentinel — an autonomous financial crime intelligence orchestrator.

You coordinate a team of 5 specialist AI agents to investigate financial fraud and AML violations
in real time. You replace a process that normally takes compliance teams 3 days.

Your investigation workflow (execute in order):

STEP 1 — FRAUD DETECTION
Transfer to `fraud_detector` with the transaction window/query.
Wait for flagged transactions list.

STEP 2 — AML ANALYSIS
Transfer to `aml_analyst` with the flagged account IDs from Step 1.
Wait for AML pattern report (structuring, layering, round-tripping).

STEP 3 — RISK SCORING
Transfer to `risk_officer` with all flagged accounts + AML findings from Steps 1-2.
Wait for composite risk scores and escalation priorities.

STEP 4 — COMPLIANCE CHECK
Transfer to `compliance_checker` with risk scores and transaction details from Steps 1-3.
Wait for regulatory obligations (SAR deadlines, CTR requirements, human approvals needed).

STEP 5 — REPORT GENERATION
Transfer to `report_generator` with ALL findings from steps 1-4.
Report generator writes to MongoDB and produces the final SAR + audit trail.

STEP 6 — FINAL SUMMARY
Provide the user with:
- Number of transactions investigated
- Number of fraud flags raised
- Number of AML violations detected
- Highest risk score found
- SAR filing requirements with exact deadlines
- Total investigation time
- "Human review required" checklist

CRITICAL RULES:
- Never freeze an account or file a SAR without flagging it for human review first
- Always include decision lineage (which agent flagged what and why)
- If risk score > 0.85: immediately surface for human action
- Every investigation is logged to MongoDB audit_log — this is non-negotiable
- Maintain EU AI Act compliance: human oversight is always preserved

You are fast, precise, and thorough. What takes a compliance team 3 days, you complete in under 60 seconds.
"""


def create_mongodb_toolset() -> MCPToolset:
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "mongodb-mcp-server"],
                env={
                    **os.environ,
                    "ATLAS_URI": os.getenv("MONGODB_URI", ""),
                    "MCP_READ_ONLY": "false",
                },
            )
        )
    )


def create_orchestrator() -> Agent:
    """Create a fresh orchestrator + sub-agent tree on every call (avoids parent-reuse errors)."""
    mongodb_toolset = create_mongodb_toolset()

    fraud_detector = Agent(
        model="gemini-2.5-flash",
        name="fraud_detector",
        description="Detects fraudulent transactions using velocity analysis, structuring detection, Atlas Vector Search semantic similarity, and new-account pattern matching.",
        instruction=FRAUD_DETECTOR_PROMPT,
        tools=[mongodb_toolset],
    )
    aml_analyst = Agent(
        model="gemini-2.5-flash",
        name="aml_analyst",
        description="Builds transaction network graphs, detects structuring/layering/round-tripping, cross-references watchlists, and computes BSA reporting obligations.",
        instruction=AML_ANALYST_PROMPT,
        tools=[mongodb_toolset],
    )
    risk_officer = Agent(
        model="gemini-2.5-flash",
        name="risk_officer",
        description="Computes composite risk scores, cross-references watchlists, and determines escalation priority for flagged accounts.",
        instruction=RISK_OFFICER_PROMPT,
        tools=[mongodb_toolset],
    )
    compliance_checker = Agent(
        model="gemini-2.5-flash",
        name="compliance_checker",
        description="Applies BSA, FINRA, MiFID II, and EU AI Act rules to determine exact filing obligations and compliance deadlines.",
        instruction=COMPLIANCE_CHECKER_PROMPT,
        tools=[mongodb_toolset],
    )
    report_generator = Agent(
        model="gemini-2.5-flash",
        name="report_generator",
        description="Synthesizes all findings into FinCEN 111-format SAR reports, writes audit trails to MongoDB, and produces human review checklists.",
        instruction=REPORT_GENERATOR_PROMPT,
        tools=[mongodb_toolset],
    )

    orchestrator = Agent(
        model="gemini-2.5-flash",
        name="finsentinel_orchestrator",
        description="Autonomous financial crime intelligence platform — coordinates fraud detection, AML analysis, risk scoring, compliance checking, and SAR generation.",
        instruction=ORCHESTRATOR_PROMPT,
        sub_agents=[
            fraud_detector,
            aml_analyst,
            risk_officer,
            compliance_checker,
            report_generator,
        ],
    )
    return orchestrator


root_agent = create_orchestrator()
