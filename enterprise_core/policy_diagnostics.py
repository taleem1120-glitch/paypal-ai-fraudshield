"""Deterministic policy diagnostics, not an empirical fraud-accuracy benchmark."""
from itertools import product
from enterprise_core.api import TransactionInput, assess, preview_assessment

AMOUNTS = ("0", "0.01", "999.99", "1000", "1000.01", "999999999.99")
CURRENCIES = ("USD", "IQD", "EUR")
FLAGS = (None, False, True)
FIELDS = ("country_mismatch", "new_account", "unusual_activity")


def diagnostics():
    counts = {"total": 0, "scored": 0, "abstained": 0,
              "high": 0, "medium": 0, "low_indicated": 0}
    violations = []
    for amount, currency, flags in product(AMOUNTS, CURRENCIES, product(FLAGS, repeat=3)):
        inputs = dict(amount=amount, currency=currency, **dict(zip(FIELDS, flags)))
        tx = TransactionInput(**inputs)
        result = assess(tx)
        counts["total"] += 1
        expected_abstention = currency != "USD" or None in flags
        if expected_abstention:
            counts["abstained"] += 1
            expected_reasons = set()
            if currency != "USD":
                expected_reasons.add("unsupported_currency")
            if None in flags:
                expected_reasons.add("missing_indicators")
            valid = (result["rule_score"] is None and result["risk_band"] == "abstain"
                     and set(result["reason_codes"]) == expected_reasons)
        else:
            counts["scored"] += 1
            score = (25 if amount in ("1000.01", "999999999.99") else 0) + sum(
                weight for flag, weight in zip(flags, (30, 20, 25)) if flag)
            band = "high" if score >= 60 else "medium" if score >= 30 else "low_indicated"
            counts[band] += 1
            valid = result["rule_score"] == score and result["risk_band"] == band
        preview = preview_assessment(tx)
        expected_bounds = None
        if currency == "USD":
            # Enumerate every consistent completion to check both endpoints independently.
            scores = [assess(TransactionInput(**(inputs | dict(zip(FIELDS, completed)))))["rule_score"]
                      for completed in product((False, True), repeat=3)
                      if all(observed is None or observed == value
                             for observed, value in zip(flags, completed))]
            expected_bounds = {"minimum": min(scores), "maximum": max(scores)}
        if not valid or result != assess(tx) or preview["possible_rule_scores"] != expected_bounds:
            violations.append({"input": inputs, "result": result})
    return {"schema": "fraudshield-policy-diagnostics-v1",
            "scope": "exhaustive synthetic grid; no observed fraud labels",
            "policy": "manual-usd-v1", "counts": counts, "violations": violations}


if __name__ == "__main__":
    import json
    result = diagnostics()
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(bool(result["violations"]))
