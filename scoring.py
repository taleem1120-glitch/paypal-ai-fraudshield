"""Pure scoring functions; non-USD amounts require conversion before USD scoring."""
from transactions import money, currency_code


# One rule catalogue supplies scoring and report explanations. Weights and
# thresholds are unchanged from the merged Phase 1 implementation.
RULES = (("amount_gt_1000_usd", "amount", 25, "Large transaction amount", "amount > 1000 USD"),
         ("country_mismatch", "country_mismatch", 30, "Country mismatch", "country_mismatch is true"),
         ("new_account", "new_account", 20, "New customer account", "new_account is true"),
         ("unusual_activity", "unusual_activity", 25, "Unusual transaction activity", "unusual_activity is true"))
FEATURE_ORDER = ("amount", "country_mismatch", "new_account", "unusual_activity")


def rule_details(amount, currency, country_mismatch=False, new_account=False, unusual_activity=False):
    amount, currency = money(amount), currency_code(currency)
    if currency != "USD":
        raise ValueError("Scoring supports USD only; no exchange rate is assumed.")
    flags = (country_mismatch, new_account, unusual_activity)
    if any(type(flag) is not bool for flag in flags):
        raise ValueError("Risk indicators must be booleans.")
    values = (amount > 1000, *flags)
    return [{"rule_id": rule_id, "input": feature, "active": active,
             "weight": weight, "contribution": weight if active else 0,
             "reason": reason, "condition": condition}
            for (rule_id, feature, weight, reason, condition), active in zip(RULES, values)]


def rule_score(amount, currency, country_mismatch=False, new_account=False, unusual_activity=False):
    details = rule_details(amount, currency, country_mismatch, new_account, unusual_activity)
    return sum(rule["contribution"] for rule in details), [rule["reason"] for rule in details if rule["active"]]


def risk_decision(score, is_anomaly):
    if score >= 60:
        return "HIGH RISK", "Manual review"
    if is_anomaly:
        return "ANOMALY DETECTED", "Review unusual transaction"
    if score >= 30:
        return "MEDIUM RISK", "Additional verification"
    return "LOW INDICATED RISK", "Routine processing (demo only)"


def train_model():
    import numpy as np
    from sklearn.ensemble import IsolationForest
    rng = np.random.default_rng(42)
    n = 3000
    data = np.column_stack([rng.lognormal(4.5, 1.0, n),
                            rng.binomial(1, .10, n), rng.binomial(1, .20, n),
                            rng.binomial(1, .08, n)])
    return IsolationForest(n_estimators=150, contamination=.08, random_state=42).fit(data)


def score_transaction(model, amount, currency, country_mismatch=False, new_account=False, unusual_activity=False):
    import math
    score, reasons = rule_score(amount, currency, country_mismatch, new_account, unusual_activity)
    features = [[float(money(amount)), int(country_mismatch), int(new_account), int(unusual_activity)]]
    predictions = model.predict(features)
    decisions = model.decision_function(features)
    if len(predictions) != 1 or len(decisions) != 1 or predictions[0] not in (-1, 1):
        raise ValueError("Invalid model result.")
    anomaly = bool(predictions[0] == -1)
    decision_score = float(decisions[0])
    if not math.isfinite(decision_score):
        raise ValueError("Invalid model result.")
    return score, reasons, anomaly, decision_score
