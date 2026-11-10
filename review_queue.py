"""Session review ordering for FraudShield's existing audit reports."""
from audit_reporting import create_audit_report
from evaluation import demonstration_cases
from scoring import risk_decision, score_transaction
from transactions import transaction_record

PRIORITIES = {
    "HIGH RISK": 0, "ANOMALY DETECTED": 1,
    "MEDIUM RISK": 2, "LOW INDICATED RISK": 3,
}
SYNTHETIC_SOURCE = "Synthetic demonstration"


def review_rows(reports):
    """Keep each analysis distinct, including repeat analyses of one order."""
    rows = []
    for report in reports:
        risk = report["risk_analysis"]
        txn = report["transaction"]
        score = risk["rule_score"]
        baseline, _ = risk_decision(score, False)
        rows.append({
            "Analysis": report["analysis_id"],
            "Source": report["source"],
            "Amount": txn["amount"],
            "Currency": txn["currency"],
            "Rules only": baseline,
            "Review priority": risk["risk_level"],
            "Rule score": score,
            "Model changed priority": baseline != risk["risk_level"],
        })
    # Equal priority and score retain arrival order.
    return sorted(rows, key=lambda r: (PRIORITIES[r["Review priority"]], -r["Rule score"]))


def synthetic_reports(model):
    reports = []
    for amount, currency, mismatch, new_account, unusual in demonstration_cases():
        score, reasons, anomaly, decision = score_transaction(
            model, amount, currency, mismatch, new_account, unusual
        )
        level, action = risk_decision(score, anomaly)
        provenance = transaction_record(amount, currency)
        provenance.update({"Source": SYNTHETIC_SOURCE, "PayPal Order ID": "N/A"})
        reports.append(create_audit_report(
            provenance, score, anomaly, decision, level, action, reasons,
            {"country_mismatch": mismatch, "new_account": new_account,
             "unusual_activity": unusual},
        ))
    return reports
