"""
Seed MongoDB finsentinel with 10,000 synthetic transactions + 6 live fraud scenarios.
Each transaction gets a Gemini text-embedding-004 vector (768-dim) for semantic
$vectorSearch — the key MongoDB Atlas differentiator for the hackathon.
"""
import os
import random
import json
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "finsentinel")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

HIGH_RISK_COUNTRIES = ["IR", "KP", "SY", "CU", "SD"]
JURISDICTIONS = ["US", "GB", "DE", "SG", "HK", "AE", "CH", "KY"] + HIGH_RISK_COUNTRIES
TRANSACTION_TYPES = ["wire_transfer", "ach", "cash_deposit", "card", "crypto", "check"]

FRAUD_DESCRIPTIONS = {
    "velocity_abuse": "Multiple rapid card transactions from same account within 30 minutes, suggesting stolen card or automated bot attack",
    "structuring": "Series of cash deposits just below $10,000 reporting threshold, classic BSA structuring / smurfing pattern",
    "round_tripping": "Funds moving through circular account chain returning to origin, indicating money laundering layering",
    "high_risk_jurisdiction": "Large wire transfer to OFAC high-risk jurisdiction from watchlisted account, potential sanctions evasion",
    "layering": "Money moving through 4 intermediary accounts before reaching destination, concealing criminal origin",
    "new_account_large_transfer": "Account opened 3 days ago transferring $45,000 to Cayman Islands — high risk new account large transfer pattern",
}

NORMAL_DESCRIPTIONS = [
    "Standard payroll wire transfer to employee account",
    "Vendor invoice payment for office supplies",
    "Customer refund processed via ACH",
    "International supplier payment for manufacturing components",
    "Routine mortgage payment",
    "Utility bill payment via ACH debit",
    "Point-of-sale card transaction at retail merchant",
    "Interbank settlement transfer",
    "Regular subscription billing charge",
    "Investment fund transfer to brokerage account",
]


def get_embedding(text: str) -> list[float]:
    """Gemini text-embedding-004 (768-dim). Falls back to deterministic pseudo-random if no key."""
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="RETRIEVAL_DOCUMENT",
            )
            return result["embedding"]
        except Exception as e:
            print(f"  [embedding API error: {e}]")
    # Deterministic fallback seeded from text hash — consistent across runs
    rng = random.Random(hash(text) & 0xFFFFFFFF)
    return [rng.gauss(0, 0.1) for _ in range(768)]


def random_account_id():
    return f"ACC-{random.randint(10000, 99999)}"


def random_amount(lo=10, hi=50000):
    return round(random.uniform(lo, hi), 2)


def seed():
    print("=" * 60)
    print("FinSentinel — MongoDB Atlas Seed")
    print("=" * 60)

    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    for col in ["transactions", "customers", "watchlists", "compliance_rules",
                "sar_reports", "audit_log"]:
        db[col].drop()

    # ── Customers ──────────────────────────────────────────────────────────────
    print("\n[1/7] Seeding customers...")
    accounts = [random_account_id() for _ in range(500)]
    customers = []
    for acc in accounts:
        age_days = random.randint(1, 2000)
        customers.append({
            "account_id": acc,
            "name": f"Customer {acc}",
            "email": f"{acc.lower().replace('-', '')}@example.com",
            "jurisdiction": random.choice(JURISDICTIONS),
            "account_opened": (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat(),
            "account_age_days": age_days,
            "risk_tier": random.choice(["LOW", "LOW", "MEDIUM", "HIGH"]),
            "kyc_verified": random.choice([True, True, True, False]),
            "baseline_monthly_avg": round(random.uniform(500, 20000), 2),
            "total_transaction_count": random.randint(5, 500),
        })
    db.customers.insert_many(customers)
    print(f"  ✓ {len(customers)} customers")

    # ── Watchlists ─────────────────────────────────────────────────────────────
    print("\n[2/7] Seeding watchlists...")
    flagged_accounts = random.sample(accounts, 20)
    watchlist_entries = [
        {
            "account_id": acc,
            "list_type": random.choice(["OFAC_SDN", "PEP", "INTERNAL_BLACKLIST", "FATF_HIGH_RISK"]),
            "reason": random.choice([
                "Designated under OFAC SDN list — sanctions violation risk",
                "Politically Exposed Person — enhanced due diligence required",
                "Internal blacklist: prior fraud conviction",
                "Associated with FATF-listed high-risk jurisdiction entity",
            ]),
            "added_date": datetime.now(timezone.utc).isoformat(),
            "risk_score": round(random.uniform(0.75, 1.0), 4),
        }
        for acc in flagged_accounts
    ]
    db.watchlists.insert_many(watchlist_entries)
    print(f"  ✓ {len(watchlist_entries)} watchlist entries")

    # ── Compliance Rules ───────────────────────────────────────────────────────
    print("\n[3/7] Seeding compliance rules...")
    rules = [
        {"rule_id": "BSA-CTR",      "regulation": "BSA",        "description": "Currency Transaction Report: cash >$10,000 in one business day",                          "threshold": 10000, "filing_type": "CTR",                 "deadline_days": 15,  "mandatory": True},
        {"rule_id": "BSA-SAR-BANK", "regulation": "BSA",        "description": "Suspicious Activity Report: suspicious transactions >$5,000",                              "threshold": 5000,  "filing_type": "SAR",                 "deadline_days": 30,  "mandatory": True},
        {"rule_id": "BSA-SAR-MSB",  "regulation": "BSA",        "description": "SAR for Money Services Businesses: suspicious activity >$2,000",                          "threshold": 2000,  "filing_type": "SAR",                 "deadline_days": 30,  "mandatory": True},
        {"rule_id": "FINRA-3310",   "regulation": "FINRA",      "description": "AML compliance program with independent annual testing",                                  "threshold": 0,     "filing_type": "PROGRAM_REVIEW",       "deadline_days": 365, "mandatory": True},
        {"rule_id": "MIFID2-ART26", "regulation": "MiFID II",   "description": "Transaction reporting to national regulator — T+1 deadline",                             "threshold": 0,     "filing_type": "TRANSACTION_REPORT",  "deadline_days": 1,   "mandatory": True},
        {"rule_id": "EUAIA-HR",     "regulation": "EU AI Act",  "description": "High-risk AI: human oversight logs required for every autonomous financial decision",     "threshold": 0,     "filing_type": "HUMAN_OVERSIGHT_LOG", "deadline_days": 0,   "mandatory": True},
        {"rule_id": "OFAC-SDN",     "regulation": "OFAC",       "description": "Block and report transactions with SDN-listed entities immediately",                      "threshold": 0,     "filing_type": "OFAC_REPORT",         "deadline_days": 1,   "mandatory": True},
        {"rule_id": "GDPR-ART22",   "regulation": "GDPR",       "description": "Right to explanation: automated decision lineage must be recorded",                       "threshold": 0,     "filing_type": "DECISION_LOG",        "deadline_days": 30,  "mandatory": True},
    ]
    db.compliance_rules.insert_many(rules)
    print(f"  ✓ {len(rules)} compliance rules")

    # ── Normal Transactions ────────────────────────────────────────────────────
    print("\n[4/7] Seeding 9,400 normal transactions (with embeddings)...")
    now = datetime.now(timezone.utc)
    transactions = []

    # Pre-compute embeddings for all normal descriptions
    desc_embeddings = {desc: get_embedding(desc) for desc in NORMAL_DESCRIPTIONS}

    for i in range(9400):
        ts = now - timedelta(hours=random.randint(0, 720))
        desc = random.choice(NORMAL_DESCRIPTIONS)
        transactions.append({
            "transaction_id": f"TXN-{random.randint(1000000, 9999999)}",
            "from_account": random.choice(accounts),
            "to_account": random.choice(accounts),
            "amount": random_amount(10, 8000),
            "currency": "USD",
            "transaction_type": random.choice(TRANSACTION_TYPES),
            "timestamp": ts.isoformat(),
            "jurisdiction": random.choice(JURISDICTIONS[:8]),
            "status": "completed",
            "description": desc,
            "embedding": desc_embeddings[desc],
            "fraud_flag": False,
            "aml_flag": False,
        })
        if (i + 1) % 2000 == 0:
            print(f"  ... {i+1}/9400")

    # ── Fraud Scenario 1: Velocity Abuse ──────────────────────────────────────
    print("\n[5/7] Embedding 6 live fraud scenarios...")
    velocity_account = random.choice(accounts)
    emb = get_embedding(FRAUD_DESCRIPTIONS["velocity_abuse"])
    for i in range(15):
        transactions.append({
            "transaction_id": f"TXN-VEL-{i:03d}",
            "from_account": velocity_account,
            "to_account": random.choice(accounts),
            "amount": random_amount(200, 1500),
            "currency": "USD",
            "transaction_type": "card",
            "timestamp": (now - timedelta(hours=2) + timedelta(minutes=i * 3)).isoformat(),
            "jurisdiction": "US",
            "status": "completed",
            "description": FRAUD_DESCRIPTIONS["velocity_abuse"],
            "embedding": emb,
            "fraud_flag": True,
            "aml_flag": False,
            "fraud_type": "velocity_abuse",
        })

    # ── Fraud Scenario 2: Structuring ─────────────────────────────────────────
    struct_dst = random.choice(accounts)
    emb = get_embedding(FRAUD_DESCRIPTIONS["structuring"])
    for i, src in enumerate(random.sample(accounts, 6)):
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
                "description": FRAUD_DESCRIPTIONS["structuring"],
                "embedding": emb,
                "fraud_flag": True,
                "aml_flag": True,
                "fraud_type": "structuring",
            })

    # ── Fraud Scenario 3: High-Risk Jurisdiction + Watchlist ──────────────────
    emb = get_embedding(FRAUD_DESCRIPTIONS["high_risk_jurisdiction"])
    for i in range(5):
        transactions.append({
            "transaction_id": f"TXN-HR-{i:03d}",
            "from_account": flagged_accounts[0],
            "to_account": random.choice(accounts),
            "amount": round(random.uniform(25000, 150000), 2),
            "currency": "USD",
            "transaction_type": "wire_transfer",
            "timestamp": (now - timedelta(hours=random.randint(1, 12))).isoformat(),
            "jurisdiction": random.choice(HIGH_RISK_COUNTRIES),
            "status": "completed",
            "description": FRAUD_DESCRIPTIONS["high_risk_jurisdiction"],
            "embedding": emb,
            "fraud_flag": True,
            "aml_flag": True,
            "fraud_type": "high_risk_jurisdiction",
        })

    # ── Fraud Scenario 4: Round-Tripping ──────────────────────────────────────
    rt_accounts = random.sample(accounts, 5)
    chain = rt_accounts + [rt_accounts[0]]
    amount = round(random.uniform(60000, 200000), 2)
    emb = get_embedding(FRAUD_DESCRIPTIONS["round_tripping"])
    for i in range(len(chain) - 1):
        transactions.append({
            "transaction_id": f"TXN-RT-{i:03d}",
            "from_account": chain[i],
            "to_account": chain[i + 1],
            "amount": round(amount * (1 - i * 0.015), 2),
            "currency": "USD",
            "transaction_type": "wire_transfer",
            "timestamp": (now - timedelta(hours=48 - i * 8)).isoformat(),
            "jurisdiction": random.choice(["KY", "CH", "SG", "AE", "US"]),
            "status": "completed",
            "description": FRAUD_DESCRIPTIONS["round_tripping"],
            "embedding": emb,
            "fraud_flag": True,
            "aml_flag": True,
            "fraud_type": "round_tripping",
        })

    # ── Fraud Scenario 5: Layering (5-hop chain) ──────────────────────────────
    layer_accounts = random.sample(accounts, 6)
    layer_amount = round(random.uniform(80000, 300000), 2)
    emb = get_embedding(FRAUD_DESCRIPTIONS["layering"])
    for i in range(len(layer_accounts) - 1):
        transactions.append({
            "transaction_id": f"TXN-LAY-{i:03d}",
            "from_account": layer_accounts[i],
            "to_account": layer_accounts[i + 1],
            "amount": round(layer_amount * (0.97 ** i), 2),
            "currency": "USD",
            "transaction_type": "wire_transfer",
            "timestamp": (now - timedelta(hours=72 - i * 12)).isoformat(),
            "jurisdiction": random.choice(["KY", "CH", "HK", "SG", "AE"]),
            "status": "completed",
            "description": FRAUD_DESCRIPTIONS["layering"],
            "embedding": emb,
            "fraud_flag": True,
            "aml_flag": True,
            "fraud_type": "layering",
        })

    # ── Fraud Scenario 6: New Account Large Transfer ──────────────────────────
    new_account = f"ACC-NEW-{random.randint(1000, 9999)}"
    db.customers.insert_one({
        "account_id": new_account,
        "name": f"Customer {new_account}",
        "email": f"{new_account.lower().replace('-', '')}@suspicious.com",
        "jurisdiction": "US",
        "account_opened": (now - timedelta(days=3)).isoformat(),
        "account_age_days": 3,
        "risk_tier": "HIGH",
        "kyc_verified": False,
        "baseline_monthly_avg": 0,
        "total_transaction_count": 0,
    })
    emb = get_embedding(FRAUD_DESCRIPTIONS["new_account_large_transfer"])
    transactions.append({
        "transaction_id": "TXN-NEW-001",
        "from_account": new_account,
        "to_account": flagged_accounts[1],
        "amount": 45000.00,
        "currency": "USD",
        "transaction_type": "wire_transfer",
        "timestamp": (now - timedelta(hours=1)).isoformat(),
        "jurisdiction": "KY",
        "status": "completed",
        "description": FRAUD_DESCRIPTIONS["new_account_large_transfer"],
        "embedding": emb,
        "fraud_flag": True,
        "aml_flag": True,
        "fraud_type": "new_account_large_transfer",
    })

    db.transactions.insert_many(transactions)
    fraud_count = sum(1 for t in transactions if t.get("fraud_flag"))
    print(f"  ✓ {len(transactions)} transactions ({fraud_count} flagged)")

    # ── Indexes ────────────────────────────────────────────────────────────────
    print("\n[6/7] Creating standard indexes...")
    db.transactions.create_index("from_account")
    db.transactions.create_index("to_account")
    db.transactions.create_index("timestamp")
    db.transactions.create_index([("from_account", 1), ("timestamp", -1)])
    db.transactions.create_index("fraud_flag")
    db.transactions.create_index("fraud_type")
    db.customers.create_index("account_id", unique=True)
    db.watchlists.create_index("account_id")
    db.compliance_rules.create_index("rule_id", unique=True)
    db.audit_log.create_index("timestamp")
    db.sar_reports.create_index("created_at")
    print("  ✓ Standard indexes created")

    # ── Atlas Vector Search Index ──────────────────────────────────────────────
    print("\n[7/7] Creating Atlas Vector Search index (fraud_vector_idx)...")
    try:
        search_index = SearchIndexModel(
            definition={
                "fields": [
                    {"type": "vector",  "path": "embedding",   "numDimensions": 768, "similarity": "cosine"},
                    {"type": "filter",  "path": "fraud_flag"},
                    {"type": "filter",  "path": "fraud_type"},
                ]
            },
            name="fraud_vector_idx",
            type="vectorSearch",
        )
        db.transactions.create_search_index(model=search_index)
        print("  ✓ Vector Search index submitted (Atlas builds it in ~2 min)")
    except Exception as e:
        print(f"  ! Vector search: {e}")
        print("  → Create in Atlas UI: Search > Create Index > vectorSearch > fraud_vector_idx")

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  Transactions : {len(transactions)}")
    print(f"  Fraud flags  : {fraud_count}")
    print(f"  Customers    : {len(customers) + 1}")
    print(f"  Watchlist    : {len(watchlist_entries)}")
    print(f"  Rules        : {len(rules)}")
    print("=" * 60)
    client.close()


if __name__ == "__main__":
    seed()
