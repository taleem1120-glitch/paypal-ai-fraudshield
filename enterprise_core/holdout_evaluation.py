"""Offline evaluation of the fixed enterprise policy on caller-supplied holdout labels."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import UUID

from .api import TransactionInput, assess

MAX_BYTES = 10 * 1024 * 1024
FIELDS = {"id", "observed_at", "label", "transaction"}


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _ratio(n, d):
    return n / d if d else None


def _metrics(rows):
    tp = fp = tn = fn = abstain_fraud = abstain_legitimate = 0
    for label, flag in rows:
        if flag is None:
            if label:
                abstain_fraud += 1
            else:
                abstain_legitimate += 1
        elif flag:
            if label:
                tp += 1
            else:
                fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    scored = tp + fp + tn + fn
    total = scored + abstain_fraud + abstain_legitimate
    return {"total": total, "scored": scored, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "abstain_fraud": abstain_fraud, "abstain_legitimate": abstain_legitimate,
            "coverage": _ratio(scored, total), "precision": _ratio(tp, tp + fp),
            "recall_scored": _ratio(tp, tp + fn),
            "recall_all": _ratio(tp, tp + fn + abstain_fraud),
            "false_positive_rate_scored": _ratio(fp, fp + tn),
            "review_rate": _ratio(tp + fp, total)}


def evaluate(raw, cutoff, *, provenance):
    """Compare fixed high-risk policy and amount-only baseline on identical coverage."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("Dataset size outside limits")
    if provenance not in ("synthetic", "authorized_holdout"):
        raise ValueError("Explicit dataset provenance required")
    boundary = _utc(cutoff)
    groups = {}
    seen = set()
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            row = json.loads(line)
            if not isinstance(row, dict) or set(row) != FIELDS or type(row["label"]) is not bool:
                raise ValueError("Invalid row")
            identifier = UUID(row["id"])
            if identifier in seen or _utc(row["observed_at"]) <= boundary:
                raise ValueError("Duplicate ID or non-holdout timestamp")
            tx = TransactionInput.model_validate(row["transaction"])
        except (TypeError, ValueError, KeyError, AttributeError):
            raise ValueError(f"Invalid holdout row {line_number}") from None
        seen.add(identifier)
        result = assess(tx)
        flag = None if result["rule_score"] is None else result["risk_band"] == "high"
        from decimal import Decimal
        baseline = None if flag is None else Decimal(tx.amount) > Decimal("1000")
        groups.setdefault(tx.currency, []).append((row["label"], flag, baseline))
    if not seen:
        raise ValueError("Empty dataset")
    def summarize(rows):
        return {"policy": _metrics([(label, flag) for label, flag, _ in rows]),
                "amount_only": _metrics([(label, baseline) for label, _, baseline in rows])}
    return {"schema": "fraudshield-holdout-v1", "policy": "manual-usd-v1",
            "dataset_sha256": hashlib.sha256(raw).hexdigest(), "cutoff_utc": boundary.isoformat(),
            "provenance": provenance, "provenance_verified": False,
            "overall": summarize([row for rows in groups.values() for row in rows]),
            "by_currency": {key: summarize(groups[key]) for key in sorted(groups)}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--provenance", choices=("synthetic", "authorized_holdout"), required=True)
    args = parser.parse_args()
    with args.dataset.open("rb") as source:
        raw = source.read(MAX_BYTES + 1)
    print(json.dumps(evaluate(raw, args.cutoff, provenance=args.provenance), sort_keys=True, indent=2))
