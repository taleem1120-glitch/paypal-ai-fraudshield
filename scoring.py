"""Pure scoring functions; non-USD amounts require conversion before USD scoring."""
from transactions import money, currency_code


def rule_score(amount, currency, country_mismatch=False, new_account=False, unusual_activity=False):
    amount, currency = money(amount), currency_code(currency)
    if currency != "USD":
        raise ValueError("Scoring supports USD only; no exchange rate is assumed.")
    rules = [(amount > 1000, 25, "Large transaction amount"),
             (country_mismatch, 30, "Country mismatch"),
             (new_account, 20, "New customer account"),
             (unusual_activity, 25, "Unusual transaction activity")]
    return sum(weight for active, weight, _ in rules if active), [reason for active, _, reason in rules if active]


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
    anomaly = bool(model.predict(features)[0] == -1)
    decision_score = float(model.decision_function(features)[0])
    if not math.isfinite(decision_score):
        raise ValueError("Invalid model result.")
    return score, reasons, anomaly, decision_score
