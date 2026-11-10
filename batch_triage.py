"""Offline synthetic/manual batch triage. Never treats anomaly output as proven fraud."""
import csv
import io
import json
import math
from hashlib import sha256
from decimal import Decimal
from scoring import rule_score, risk_decision, train_model, score_transaction

REQUIRED = ("case_id", "amount_usd", "country_mismatch", "new_account", "unusual_activity")
MAX_CASES = 200
MAX_BYTES = 50000

def _flag(value):
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes"): return True
    if normalized in ("0", "false", "no"): return False
    raise ValueError("Flags must be yes/no, true/false or 1/0.")

def parse_batch(csv_text):
    if not isinstance(csv_text, str) or len(csv_text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV exceeds the 50 KB safety limit.")
    reader = csv.DictReader(io.StringIO(csv_text, newline=""), strict=True)
    if not reader.fieldnames or tuple(reader.fieldnames) != REQUIRED:
        raise ValueError("Use exactly these five columns in order: " + ", ".join(REQUIRED))
    result, seen = [], set()
    for line, row in enumerate(reader, 2):
        if len(result) >= MAX_CASES: raise ValueError("Maximum 200 cases per analysis.")
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Invalid number of fields on row {line}.")
        case_id = row["case_id"].strip()
        if not (1 <= len(case_id) <= 48) or not all(c.isalnum() or c in "-_" for c in case_id):
            raise ValueError(f"Invalid case ID on row {line}. Use letters, digits, - or _.")
        if case_id in seen: raise ValueError(f"Duplicate case ID: {case_id}")
        seen.add(case_id)
        try:
            amount = Decimal(row["amount_usd"].strip())
            if not amount.is_finite() or not (Decimal("0") <= amount <= Decimal("1000000000")):
                raise ValueError()
            if amount.as_tuple().exponent < -2: raise ValueError()
            flags = [_flag(row[key]) for key in REQUIRED[2:]]
        except (ValueError, ArithmeticError):
            raise ValueError(f"Invalid USD amount or flag on row {line}.") from None
        result.append((case_id, str(amount), *flags))
    if not result: raise ValueError("Provide at least one case.")
    return result

def triage(csv_text, model=None):
    model = train_model() if model is None else model
    findings = []
    for case_id, amount, mismatch, new, unusual in parse_batch(csv_text):
        score, reasons, anomaly, decision = score_transaction(
            model, amount, "USD", mismatch, new, unusual)
        if not math.isfinite(decision): raise ValueError("Non-finite anomaly score.")
        band, recommendation = risk_decision(score, anomaly)
        findings.append({
            "case_id": case_id, "amount_usd": amount,
            "rule_score": score, "anomaly": anomaly,
            "anomaly_decision_score": round(decision, 6),
            "risk_band": band, "recommendation": recommendation,
            "reason_codes": reasons or ["No configured rule indicators"],
            "indicator_source": "manual_or_synthetic_not_paypal_verified",
        })
    # Prioritize human analyst attention, never approve/deny transactions.
    findings.sort(key=lambda x: (-x["rule_score"], -int(x["anomaly"]), x["case_id"]))
    for i, entry in enumerate(findings, 1): entry["review_priority"] = i
    payload = {
        "schema": "fraudshield.batch.v1", "case_count": len(findings),
        "data_provenance": "user-entered synthetic/manual values",
        "validation": "No real-world fraud precision, recall or detection claims",
        "automated_payment_actions": False, "findings": findings,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"payload": payload, "sha256": sha256(raw.encode("utf-8")).hexdigest()}

def verify_batch_audit(raw):
    """Verify document self-consistency; a SHA-256 digest is NOT a signature."""
    try:
        if isinstance(raw, bytes):
            if len(raw) > 1000000:
                return False
            raw = raw.decode("utf-8")
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 1000000:
            return False
        doc = json.loads(raw)
        if not isinstance(doc, dict) or set(doc) != {"payload", "sha256"}:
            return False
        payload = doc["payload"]
        if not isinstance(payload, dict):
            return False
        if payload.get("schema") != "fraudshield.batch.v1":
            return False
        rows = payload.get("findings")
        if not isinstance(rows, list) or not (1 <= len(rows) <= MAX_CASES):
            return False
        if payload.get("case_count") != len(rows) or payload.get("automated_payment_actions") is not False:
            return False
        digest = doc["sha256"]
        if not isinstance(digest, str) or len(digest) != 64:
            return False
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        from hmac import compare_digest
        return compare_digest(sha256(canonical.encode("utf-8")).hexdigest(), digest)
    except (ValueError, UnicodeError, TypeError, OverflowError, KeyError):
        return False
