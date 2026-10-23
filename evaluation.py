"""Offline, synthetic-only model diagnostics; not a validated fraud benchmark."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationSummary:
    total: int
    flagged: int
    anomaly_rate: float
    average_rule_score: float
    agreement_rate: float


def evaluate_synthetic_cases(model, cases):
    """Evaluate predefined scenarios without sending data to PayPal or storing PII.

    Each case is (amount, currency, country_mismatch, new_account,
    unusual_activity). This reports agreement between two heuristics, NOT
    fraud accuracy. No ground-truth fraud labels exist here.
    """
    from scoring import score_transaction

    results = []
    for case in cases:
        if len(case) != 5:
            raise ValueError("Each scenario must have five fields.")
        score, _, anomaly, decision = score_transaction(model, *case)
        results.append({"rule_score": score, "anomaly": anomaly,
                        "decision_score": decision, "rule_flag": score >= 60})
    if not results:
        raise ValueError("At least one synthetic scenario is required.")
    total = len(results)
    flagged = sum(item["anomaly"] for item in results)
    agreements = sum(item["rule_flag"] == item["anomaly"] for item in results)
    return EvaluationSummary(
        total=total,
        flagged=flagged,
        anomaly_rate=flagged / total,
        average_rule_score=sum(item["rule_score"] for item in results) / total,
        agreement_rate=agreements / total,
    )


def demonstration_cases():
    """Hand-picked examples; deliberately NOT random, representative, or real fraud data."""
    return [
        (1.0, "USD", False, False, False),
        (100.0, "USD", False, True, True),
        (1001.0, "USD", True, True, True),
        (25.0, "USD", True, False, False),
        (850.0, "USD", False, False, True),
        (2000.0, "USD", False, True, False),
    ]
