import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from agent.agents.fraud_detector import fraud_detector_agent
from agent.agents.aml_analyst import aml_analyst_agent
from agent.agents.risk_officer import risk_officer_agent
from agent.agents.compliance_checker import compliance_checker_agent
from agent.agents.report_generator import report_generator_agent

ORCHESTRATOR_PROMPT = """
You are FinSentinel — an autonomous financial crime intelligence orchestrator.

You coordinate a team of 5 specialist AI agents to investigate financial fraud and AML violations
in real time. You replace a process that normally takes compliance teams 3 days.

Your investigation workflow (execute in order):

STEP 1 — FRAUD DETECTION
Transfer to `fraud_detector` with the transaction window/query.
Wait for flagged transactions list.

STEP 2 — AML ANALYSIS
Transfer to `aml_analyst` with the flagged account IDs.
Wait for AML pattern report (structuring, layering, round-tripping).

STEP 3 — RISK SCORING
Transfer to `risk_officer` with all flagged accounts + AML findings.
Wait for composite risk scores and escalation priorities.

STEP 4 — COMPLIANCE CHECK
Transfer to `compliance_checker` with risk scores and transaction details.
Wait for regulatory obligations (SAR deadlines, CTR requirements, human approvals needed).

STEP 5 — REPORT GENERATION
Transfer to `report_generator` with ALL findings from steps 1-4.
Report generator writes to MongoDB and produces the final SAR + audit trail.

STEP 6 — FINAL SUMMARY
Provide the user with:
- Number of transactions investigated
- Number of fraud flags
- Number of AML violations
- Highest risk score found
- SAR filing requirements with deadlines
- Total time taken
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
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "ATLAS_URI": os.getenv("MONGODB_URI", ""),
                "MCP_READ_ONLY": "false",
            },
        )
    )

def create_orchestrator() -> Agent:
    mongodb_toolset = create_mongodb_toolset()

    fraud_detector_agent.tools = [mongodb_toolset]
    aml_analyst_agent.tools = [mongodb_toolset]
    risk_officer_agent.tools = [mongodb_toolset]
    compliance_checker_agent.tools = [mongodb_toolset]
    report_generator_agent.tools = [mongodb_toolset]

    orchestrator = Agent(
        model="gemini-2.5-flash",
        name="finsentinel_orchestrator",
        description="Autonomous financial crime intelligence platform — coordinates fraud detection, AML analysis, risk scoring, compliance checking, and SAR generation.",
        instruction=ORCHESTRATOR_PROMPT,
        sub_agents=[
            fraud_detector_agent,
            aml_analyst_agent,
            risk_officer_agent,
            compliance_checker_agent,
            report_generator_agent,
        ],
    )
    return orchestrator

root_agent = create_orchestrator()
