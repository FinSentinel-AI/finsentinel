import math
from datetime import datetime, timezone


def calculate_velocity_score(transactions: list[dict], window_hours: int = 1) -> float:
    """Score 0-1 based on transaction frequency within the window."""
    if not transactions:
        return 0.0
    count = len(transactions)
    # >10 txns/hour = score 1.0; linear scale below
    return min(count / 10.0, 1.0)


def calculate_anomaly_score(amount: float, baseline_avg: float, baseline_std: float) -> float:
    """Z-score based anomaly detection, mapped to 0-1."""
    if baseline_std == 0:
        return 0.0
    z = abs(amount - baseline_avg) / baseline_std
    # z-score of 3 maps to ~0.95 score
    return min(1 - math.exp(-z / 3), 1.0)


def calculate_composite_risk(
    fraud_score: float,
    aml_score: float,
    watchlist_match: bool,
    account_age_days: int,
    jurisdiction_risk: float,
) -> float:
    watchlist_component = 1.0 if watchlist_match else 0.0
    age_component = max(0.0, 1.0 - (account_age_days / 365))

    score = (
        fraud_score * 0.30
        + aml_score * 0.25
        + watchlist_component * 0.25
        + age_component * 0.10
        + jurisdiction_risk * 0.10
    )
    return round(min(score, 1.0), 4)


def get_escalation_priority(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "CRITICAL"
    if risk_score >= 0.65:
        return "HIGH"
    if risk_score >= 0.40:
        return "MEDIUM"
    return "LOW"


def sar_required(total_amount: float, is_bank: bool = True) -> bool:
    threshold = 5000 if is_bank else 2000
    return total_amount >= threshold


def structuring_detected(deposits: list[float], threshold: float = 10000.0) -> bool:
    """Detects if multiple deposits are structured to stay below reporting threshold."""
    if sum(deposits) < threshold:
        return False
    return all(d < threshold for d in deposits) and sum(deposits) >= threshold
