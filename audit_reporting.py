
"""FraudShield AI - Phase 3 Audit Reporting.

Offline audit report creation and integrity verification.
No external API calls or persistent storage.
"""

import hashlib
import hmac
import json
import uuid

from datetime import datetime, timezone
from decimal import Decimal


SCHEMA_VERSION = "1.0"


def utc_now():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def new_analysis_id():
    """Generate a unique analysis identifier."""
    return str(uuid.uuid4())


def json_default(value):
    """Convert supported values into JSON-safe values."""
    if isinstance(value, Decimal):
        return str(value)

    raise TypeError("Unsupported report value")


def canonical_json(data):
    """Generate deterministic JSON for hashing."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=json_default,
    )


def calculate_sha256(data):
    """Calculate the SHA-256 digest of canonical JSON."""
    encoded = canonical_json(data).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_audit_report(
    provenance,
    rule_score,
    anomaly,
    anomaly_score,
    risk_level,
    recommended_action,
    reasons,
):
    """Create an independent audit report.

    Records supplied analysis information without
    independently verifying PayPal transactions.
    """

    report = {
        "schema_version": SCHEMA_VERSION,
        "analysis_id": new_analysis_id(),
        "generated_at_utc": utc_now(),
        "source": provenance.get("Source", "Unknown"),
        "transaction": {
            "order_id": provenance.get(
                "PayPal Order ID", "Manual"
            ),
            "order_status": provenance.get(
                "PayPal Order Status", "N/A"
            ),
            "order_retrieved_at": provenance.get(
                "Order Retrieved At", "N/A"
            ),
            "analyzed_at": provenance.get(
                "Analyzed At", "N/A"
            ),
            "amount": str(
                provenance.get("Amount", "")
            ),
            "currency": provenance.get(
                "Currency", ""
            ),
        },
        "risk_analysis": {
            "rule_score": int(rule_score),
            "ml_anomaly": bool(anomaly),
            "ml_decision_score": float(anomaly_score),
            "risk_level": str(risk_level),
            "recommended_action": str(
                recommended_action
            ),
            "reasons": list(reasons),
        },
        "limitations": (
            "Prototype analysis using synthetic ML "
            "training data. Not proof of fraud or "
            "a validated real-world detection result."
        ),
    }

    report["integrity"] = {
        "algorithm": "SHA-256",
        "digest": calculate_sha256(report),
    }

    return report


def verify_audit_report(report):
    """Verify the SHA-256 content digest.

    Detects content changes but does not establish
    authorship, provenance authenticity, or prevent
    someone from recomputing an altered digest.
    """

    if not isinstance(report, dict):
        return False

    integrity = report.get("integrity")

    if not isinstance(integrity, dict):
        return False

    if integrity.get("algorithm") != "SHA-256":
        return False

    digest = integrity.get("digest")

    if not isinstance(digest, str):
        return False

    if len(digest) != 64:
        return False

    content = {
        key: value
        for key, value in report.items()
        if key != "integrity"
    }

    try:
        expected = calculate_sha256(content)
    except (TypeError, ValueError, OverflowError):
        return False

    return hmac.compare_digest(expected, digest)


def export_audit_json(report):
    """Export the report as human-readable UTF-8 JSON."""

    return json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
        default=json_default,
    )
