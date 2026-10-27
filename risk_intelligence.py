"""Transparent synthetic rule sensitivity lab; not a validated fraud classifier."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

@dataclass(frozen=True)
class Scenario:
    name: str
    amount_usd: str
    country_mismatch: bool = False
    new_account: bool = False
    unusual_activity: bool = False

SCENARIOS = (
    Scenario("Ordinary checkout", "18.00"),
    Scenario("New account", "25.00", new_account=True),
    Scenario("Cross-border high value", "1800.00", country_mismatch=True),
    Scenario("Multiple flags", "1850.00", True, True, True),
    Scenario("Unusual low value", "12.00", unusual_activity=True),
)

def explain(s):
    try:
        amount = Decimal(str(s.amount_usd))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid amount") from None
    if not amount.is_finite() or amount < 0 or amount > Decimal("1000000000"):
        raise ValueError("Amount outside demo limits")
    indicators = (
        (amount > 1000, 25, "amount_over_1000_usd"),
        (s.country_mismatch, 30, "manual_country_mismatch"),
        (s.new_account, 20, "manual_new_account"),
        (s.unusual_activity, 25, "manual_unusual_activity"),
    )
    score = sum(weight for active, weight, _ in indicators if active)
    return {"scenario": s.name, "amount_usd": str(amount), "rule_score": score,
            "risk_band": "high" if score >= 60 else ("medium" if score >= 30 else "low_indicated"),
            "reason_codes": [code for active, _, code in indicators if active],
            "source": "synthetic_manual_indicators"}

def counterfactuals(s):
    from dataclasses import replace
    base = explain(s)["rule_score"]
    return [{"indicator": field, "baseline_score": base,
             "score_if_toggled": explain(replace(s, **{field: not getattr(s, field)}))["rule_score"]}
            for field in ("country_mismatch", "new_account", "unusual_activity")]

def report(scenarios=SCENARIOS):
    payload = {"schema": "fraudshield.synthetic.v1",
               "accuracy_claim": "none; no verified fraud labels",
               "cases": [explain(s) for s in scenarios]}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {"payload": payload, "sha256": sha256(raw.encode("utf-8")).hexdigest()}

def verify_report(document):
    try:
        raw = json.dumps(document["payload"], sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest() == document["sha256"]
    except (TypeError, ValueError, KeyError):
        return False
