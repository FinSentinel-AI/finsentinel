"""
Seed MongoDB with synthetic financial data: 10,000 transactions,
customers, watchlists, compliance rules, and embedded fraud scenarios.
"""
import os
import random
import json
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "finsentinel")

HIGH_RISK_COUNTRIES = ["IR", "KP", "SY", "CU", "SD"]
JURISDICTIONS = ["US", "GB", "DE", "SG", "HK", "AE", "CH", "KY"] + HIGH_RISK_COUNTRIES
TRANSACTION_TYPES = ["wire_transfer", "ach", "cash_deposit", "card", "crypto", "check"]

def random_account_id(prefix="ACC"):
    return f"{prefix}-{random.randint(10000, 99999)}"

def random_amount(lo=10, hi=50000):
    return round(random.uniform(lo, hi), 2)

def seed():
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    print("Dropping existing collections...")
    for col in ["transactions", "customers", "watchlists", "compliance_rules",
                "sar_reports", "audit_log"]:
        db[col].drop()

    # ── Customers ──────────────────────────────────────────────────────────────
    print("Seeding customers...")
    accounts = [random_account_id() for _ in range(500)]
    customers = []
    for acc in accounts:
        age_days = random.randint(1, 2000)
        customers.append({
            "account_id": acc,
            "name": f"Customer {acc}",
            "email": f"{acc.lower()}@example.com",
            "jurisdiction": random.choice(JURISDICTIONS),
            "account_opened": (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat(),
            "account_age_days": age_days,
            "risk_tier": random.choice(["LOW", "MEDIUM", "HIGH"]),
            "kyc_verified": random.choice([True, True, True, False]),
        })
    db.customers.insert_many(customers)

    # ── Watchlists ─────────────────────────────────────────────────────────────
    print("Seeding watchlists...")
    flagged = random.sample(accounts, 15)
    watchlist_entries = [
        {"account_id": acc, "list_type": random.choice(["OFAC_SDN", "PEP", "INTERNAL_BLACKLIST"]),
         "reason": "Sanctioned entity", "added_date": datetime.now(timezone.utc).isoformat()}
        for acc in flagged
    ]
    db.watchlists.insert_many(watchlist_entries)

    # ── Compliance Rules ───────────────────────────────────────────────────────
    print("Seeding compliance rules...")
    rules = [
        {"rule_id": "BSA-CTR", "regulation": "BSA", "description": "Cash Transaction Report required for cash >$10,000 in one business day", "threshold": 10000, "filing_type": "CTR", "deadline_days": 15},
        {"rule_id": "BSA-SAR-BANK", "regulation": "BSA", "description": "Suspicious Activity Report for transactions >$5,000 with suspicious indicators", "threshold": 5000, "filing_type": "SAR", "deadline_days": 30},
        {"rule_id": "BSA-SAR-MSB", "regulation": "BSA", "description": "SAR for MSBs: suspicious activity >$2,000", "threshold": 2000, "filing_type": "SAR", "deadline_days": 30},
        {"rule_id": "FINRA-3310", "regulation": "FINRA", "description": "AML program with independent testing annually", "threshold": 0, "filing_type": "PROGRAM_REVIEW", "deadline_days": 365},
        {"rule_id": "MIFID2-ART26", "regulation": "MiFID II", "description": "Transaction reporting to national authority within T+1", "threshold": 0, "filing_type": "TRANSACTION_REPORT", "deadline_days": 1},
        {"rule_id": "EUAIA-HR", "regulation": "EU AI Act", "description": "High-risk AI: human oversight required for autonomous financial decisions", "threshold": 0, "filing_type": "HUMAN_OVERSIGHT_LOG", "deadline_days": 0},
        {"rule_id": "OFAC-SDN", "regulation": "OFAC", "description": "Transactions with SDN-listed entities must be blocked and reported immediately", "threshold": 0, "filing_type": "OFAC_REPORT", "deadline_days": 1},
    ]
    db.compliance_rules.insert_many(rules)

    # ── Normal Transactions ────────────────────────────────────────────────────
    print("Seeding 9,500 normal transactions...")
    now = datetime.now(timezone.utc)
    transactions = []
    for _ in range(9500):
        ts = now - timedelta(hours=random.randint(0, 720))
        src = random.choice(accounts)
        dst = random.choice(accounts)
        transactions.append({
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "from_account": src,
            "to_account": dst,
            "amount": random_amount(10, 8000),
            "currency": "USD",
            "transaction_type": random.choice(TRANSACTION_TYPES),
            "timestamp": ts.isoformat(),
            "jurisdiction": random.choice(JURISDICTIONS[:8]),
            "status": "completed",
            "fraud_flag": False,
            "aml_flag": False,
        })

    # ── Fraud Scenario 1: Velocity Abuse ──────────────────────────────────────
    print("Embedding fraud scenario 1: velocity abuse...")
    velocity_account = random.choice(accounts)
    base_time = now - timedelta(hours=2)
    for i in range(12):
        transactions.append({
            "transaction_id": f"TXN-VEL-{i:03d}",
            "from_account": velocity_account,
            "to_account": random.choice(accounts),
            "amount": random_amount(200, 1500),
            "currency": "USD",
            "transaction_type": "card",
            "timestamp": (base_time + timedelta(minutes=i * 4)).isoformat(),
            "jurisdiction": "US",
            "status": "completed",
            "fraud_flag": True,
            "fraud_type": "velocity_abuse",
        })

    # ── Fraud Scenario 2: Structuring (Smurfing) ──────────────────────────────
    print("Embedding fraud scenario 2: structuring...")
    structuring_accounts = random.sample(accounts, 5)
    struct_dst = random.choice(accounts)
    for i, src in enumerate(structuring_accounts):
        for j in range(3):
            transactions.append({
                "transaction_id": f"TXN-STR-{i}{j}",
                "from_account": src,
                "to_account": struct_dst,
                "amount": round(random.uniform(8500, 9900), 2),
                "currency": "USD",
                "transaction_type": "cash_deposit",
                "timestamp": (now - timedelta(hours=random.randint(1, 48))).isoformat(),
                "jurisdiction": "US",
                "status": "completed",
                "fraud_flag": True,
                "aml_flag": True,
                "fraud_type": "structuring",
            })

    # ── Fraud Scenario 3: High-Risk Jurisdiction + Watchlist ──────────────────
    print("Embedding fraud scenario 3: high-risk jurisdiction...")
    watchlist_account = flagged[0]
    for i in range(4):
        transactions.append({
            "transaction_id": f"TXN-HR-{i:03d}",
            "from_account": watchlist_account,
            "to_account": random.choice(accounts),
            "amount": round(random.uniform(15000, 75000), 2),
            "currency": "USD",
            "transaction_type": "wire_transfer",
            "timestamp": (now - timedelta(hours=random.randint(1, 12))).isoformat(),
            "jurisdiction": random.choice(HIGH_RISK_COUNTRIES),
            "status": "completed",
            "fraud_flag": True,
            "aml_flag": True,
            "fraud_type": "high_risk_jurisdiction",
        })

    # ── Fraud Scenario 4: Round-Tripping ──────────────────────────────────────
    print("Embedding fraud scenario 4: round-tripping...")
    rt_accounts = random.sample(accounts, 4)
    amount = round(random.uniform(40000, 90000), 2)
    chain = rt_accounts + [rt_accounts[0]]
    for i in range(len(chain) - 1):
        transactions.append({
            "transaction_id": f"TXN-RT-{i:03d}",
            "from_account": chain[i],
            "to_account": chain[i + 1],
            "amount": round(amount * (1 - i * 0.02), 2),
            "currency": "USD",
            "transaction_type": "wire_transfer",
            "timestamp": (now - timedelta(hours=24 - i * 5)).isoformat(),
            "jurisdiction": random.choice(["KY", "CH", "SG", "US"]),
            "status": "completed",
            "fraud_flag": True,
            "aml_flag": True,
            "fraud_type": "round_tripping",
        })

    db.transactions.insert_many(transactions)
    print(f"Inserted {len(transactions)} transactions total.")

    # ── Vector Search Index (Atlas) ────────────────────────────────────────────
    print("""
NOTE: To enable vector search on MongoDB Atlas, create this index on 'transactions':
{
  "name": "fraud_vector_idx",
  "type": "vectorSearch",
  "definition": {
    "fields": [{ "type": "vector", "path": "embedding", "numDimensions": 768, "similarity": "cosine" }]
  }
}
You can do this in the Atlas UI under Search > Create Search Index.
""")
    print("Seed complete.")
    client.close()


if __name__ == "__main__":
    seed()
