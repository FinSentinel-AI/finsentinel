"""
Pre-fetch MongoDB data before agents run.
This eliminates per-agent tool calls (5-8 LLM turns → 1 LLM turn per agent).
"""
import os
import json
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient


def _client() -> MongoClient:
    return MongoClient(os.getenv("MONGODB_URI", ""), serverSelectionTimeoutMS=10000)


def fetch_investigation_context() -> dict:
    """
    Pull all data needed for the 5-agent pipeline from MongoDB in one shot.
    Returns a dict with all relevant records.
    """
    now = datetime.now(timezone.utc)
    window_24h = (now - timedelta(hours=24)).isoformat()
    window_48h = (now - timedelta(hours=48)).isoformat()
    window_7d  = (now - timedelta(days=7)).isoformat()
    window_30d = (now - timedelta(days=30)).isoformat()

    client = _client()
    db = client["finsentinel"]

    ctx = {}

    # 1. All fraud-flagged transactions
    ctx["fraud_flagged"] = list(db.transactions.find(
        {"fraud_flag": True},
        {"_id": 0, "transaction_id": 1, "from_account": 1, "to_account": 1,
         "amount": 1, "transaction_type": 1, "timestamp": 1, "fraud_type": 1,
         "jurisdiction": 1, "description": 1}
    ).limit(100))

    # 2. Velocity abuse — accounts with >5 transactions in 24h
    ctx["velocity_accounts"] = list(db.transactions.aggregate([
        {"$match": {"timestamp": {"$gte": window_24h}}},
        {"$group": {"_id": "$from_account", "count": {"$sum": 1},
                    "total": {"$sum": "$amount"}, "types": {"$addToSet": "$transaction_type"}}},
        {"$match": {"$or": [{"count": {"$gte": 5}}, {"total": {"$gte": 50000}}]}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]))

    # 3. Structuring candidates — cash deposits $8K-$9.9K
    ctx["structuring_candidates"] = list(db.transactions.aggregate([
        {"$match": {"transaction_type": "cash_deposit",
                    "amount": {"$gte": 8000, "$lte": 9999},
                    "timestamp": {"$gte": window_48h}}},
        {"$group": {"_id": "$to_account", "deposits": {"$push": "$amount"},
                    "count": {"$sum": 1}, "total": {"$sum": "$amount"}}},
        {"$match": {"count": {"$gte": 3}, "total": {"$gte": 10000}}},
        {"$sort": {"total": -1}},
        {"$limit": 20}
    ]))

    # 4. High-risk jurisdiction transactions
    ctx["high_risk_txns"] = list(db.transactions.find(
        {"jurisdiction": {"$in": ["IR", "KP", "SY", "CU", "SD"]},
         "timestamp": {"$gte": window_7d}},
        {"_id": 0, "transaction_id": 1, "from_account": 1, "to_account": 1,
         "amount": 1, "jurisdiction": 1, "timestamp": 1}
    ).sort("amount", -1).limit(20))

    # 5. New accounts (<30 days) with large transfers
    ctx["new_account_large_txns"] = list(db.transactions.aggregate([
        {"$match": {"timestamp": {"$gte": window_30d}, "amount": {"$gte": 10000}}},
        {"$lookup": {
            "from": "customers",
            "localField": "from_account",
            "foreignField": "account_id",
            "as": "customer"
        }},
        {"$unwind": "$customer"},
        {"$match": {"customer.onboarding_date": {"$gte": window_30d}}},
        {"$project": {"_id": 0, "transaction_id": 1, "from_account": 1,
                      "amount": 1, "timestamp": 1, "customer.risk_level": 1}},
        {"$limit": 10}
    ]))

    # 6. Watchlist entries
    ctx["watchlist"] = list(db.watchlists.find(
        {}, {"_id": 0, "account_id": 1, "list_type": 1, "reason": 1, "added_date": 1}
    ).limit(100))

    # 7. High-risk customers
    ctx["high_risk_customers"] = list(db.customers.find(
        {"risk_level": "high"},
        {"_id": 0, "account_id": 1, "name": 1, "risk_level": 1,
         "onboarding_date": 1, "pep_flag": 1, "country": 1}
    ).limit(50))

    # 8. Compliance rules
    ctx["compliance_rules"] = list(db.compliance_rules.find(
        {}, {"_id": 0, "regulation": 1, "rule_id": 1, "description": 1,
             "threshold": 1, "filing_type": 1, "deadline_days": 1}
    ).limit(20))

    # 9. Money flow network for fraud-flagged accounts
    fraud_accounts = list(set(
        [t["from_account"] for t in ctx["fraud_flagged"]]
        + [t["to_account"] for t in ctx["fraud_flagged"]]
    ))[:20]
    if fraud_accounts:
        ctx["money_flow_network"] = list(db.transactions.aggregate([
            {"$match": {
                "$or": [{"from_account": {"$in": fraud_accounts}},
                        {"to_account": {"$in": fraud_accounts}}],
                "timestamp": {"$gte": window_7d}
            }},
            {"$group": {
                "_id": {"src": "$from_account", "dst": "$to_account"},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
                "txn_ids": {"$push": "$transaction_id"}
            }},
            {"$sort": {"total": -1}},
            {"$limit": 30}
        ]))
    else:
        ctx["money_flow_network"] = []

    # Stats
    ctx["_stats"] = {
        "total_transactions": db.transactions.count_documents({}),
        "fraud_flagged_count": len(ctx["fraud_flagged"]),
        "velocity_suspects": len(ctx["velocity_accounts"]),
        "structuring_suspects": len(ctx["structuring_candidates"]),
        "high_risk_txn_count": len(ctx["high_risk_txns"]),
        "watchlist_count": len(ctx["watchlist"]),
        "fetch_timestamp": now.isoformat(),
    }

    client.close()
    return ctx


def context_to_text(ctx: dict) -> str:
    """Convert the fetched context dict to a compact text representation."""
    lines = [
        f"=== MONGODB FINSENTINEL DATABASE SNAPSHOT ===",
        f"Fetch time: {ctx['_stats']['fetch_timestamp']}",
        f"Total transactions: {ctx['_stats']['total_transactions']}",
        f"",
    ]

    if ctx["fraud_flagged"]:
        lines.append(f"FRAUD-FLAGGED TRANSACTIONS ({len(ctx['fraud_flagged'])} records):")
        for t in ctx["fraud_flagged"][:20]:
            lines.append(
                f"  {t.get('transaction_id','')} | {t.get('from_account','')} → {t.get('to_account','')} | "
                f"${t.get('amount',0):,.2f} | {t.get('transaction_type','')} | {t.get('fraud_type','')} | "
                f"{t.get('timestamp','')[:10]}"
            )
        lines.append("")

    if ctx["velocity_accounts"]:
        lines.append(f"VELOCITY ABUSE SUSPECTS (>5 txns/24h or >$50K/24h):")
        for a in ctx["velocity_accounts"]:
            lines.append(
                f"  {a['_id']}: {a['count']} transactions, ${a['total']:,.2f} total, types={a['types']}"
            )
        lines.append("")

    if ctx["structuring_candidates"]:
        lines.append(f"STRUCTURING CANDIDATES (cash deposits $8K-$9.9K, total ≥$10K):")
        for a in ctx["structuring_candidates"]:
            lines.append(
                f"  {a['_id']}: {a['count']} deposits totaling ${a['total']:,.2f}, "
                f"amounts={[round(x,0) for x in a['deposits'][:5]]}"
            )
        lines.append("")

    if ctx["high_risk_txns"]:
        lines.append(f"HIGH-RISK JURISDICTION TRANSACTIONS (IR/KP/SY/CU/SD):")
        for t in ctx["high_risk_txns"][:10]:
            lines.append(
                f"  {t.get('transaction_id','')} | {t.get('from_account','')} → {t.get('to_account','')} | "
                f"${t.get('amount',0):,.2f} | {t.get('jurisdiction','')} | {t.get('timestamp','')[:10]}"
            )
        lines.append("")

    if ctx["watchlist"]:
        lines.append(f"WATCHLIST ENTRIES ({len(ctx['watchlist'])} total):")
        for w in ctx["watchlist"][:10]:
            lines.append(
                f"  {w.get('account_id','')} | {w.get('list_type','')} | {w.get('reason','')}"
            )
        lines.append("")

    if ctx["high_risk_customers"]:
        lines.append(f"HIGH-RISK CUSTOMERS ({len(ctx['high_risk_customers'])} total):")
        for c in ctx["high_risk_customers"][:10]:
            lines.append(
                f"  {c.get('account_id','')} | {c.get('name','')} | {c.get('country','')} | "
                f"PEP={c.get('pep_flag', False)}"
            )
        lines.append("")

    if ctx["money_flow_network"]:
        lines.append(f"MONEY FLOW NETWORK (fraud-account transfers):")
        for f in ctx["money_flow_network"][:10]:
            lines.append(
                f"  {f['_id']['src']} → {f['_id']['dst']}: ${f['total']:,.2f} ({f['count']} txns)"
            )
        lines.append("")

    if ctx["compliance_rules"]:
        lines.append(f"COMPLIANCE RULES IN EFFECT:")
        for r in ctx["compliance_rules"][:8]:
            lines.append(
                f"  [{r.get('rule_id','')}] {r.get('regulation','')} — {r.get('description','')[:80]}"
            )
        lines.append("")

    lines.append(f"=== END MONGODB SNAPSHOT ===")
    return "\n".join(lines)
