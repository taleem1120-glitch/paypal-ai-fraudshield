"""Offline, bounded integrity checks for FraudShield audit JSON variants.

A matching embedded SHA-256 is not an independent signature or attestation.
"""
import hashlib
import hmac
import json
import re

from audit_reporting import verify_audit_report

MAX_AUDIT_BYTES = 1024 * 1024
_HEX64 = re.compile(r"[a-fA-F0-9]{64}\Z")


def _digest(value):
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _match_digest(value, expected):
    return (isinstance(expected, str) and _HEX64.fullmatch(expected) is not None
            and hmac.compare_digest(_digest(value), expected.lower()))


def verify_v2_audit(document):
    """Validate v2 case and complete-report digests, plus essential structure."""
    if not isinstance(document, dict) or document.get("schema") != "fraudshield-audit-v2":
        return False
    case, assessment = document.get("case"), document.get("assessment")
    if not isinstance(case, dict) or not isinstance(assessment, dict):
        return False
    if not isinstance(case.get("id"), str) or not case["id"]:
        return False
    if type(assessment.get("score")) is not int or not 0 <= assessment["score"] <= 100:
        return False
    if assessment.get("band") not in ("Low", "Medium", "High"):
        return False
    hits = assessment.get("hits")
    if not isinstance(hits, list) or any(
        not isinstance(hit, dict)
        or not isinstance(hit.get("rule"), str)
        or type(hit.get("points")) is not int
        or hit["points"] < 0 for hit in hits
    ):
        return False
    if min(100, sum(hit["points"] for hit in hits)) != assessment["score"]:
        return False
    if type(document.get("ai_provider_verified")) is not bool:
        return False
    if document.get("ai_provider_verified") or document.get("ai_review") is not None:
        # This verifier supports only the unsigned synthetic v2 export, not
        # provider-attested AI review or third-party evidence.
        return False
    if not isinstance(document.get("limitations"), list) or not isinstance(document.get("generated_utc"), str):
        return False
    if not _match_digest(case, assessment.get("sha256")):
        return False
    try:
        return bool(_match_digest(
            {key: value for key, value in document.items() if key != "report_sha256"},
            document.get("report_sha256"),
        ))
    except (TypeError, ValueError, OverflowError):
        return False


def verify_uploaded_audit(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_AUDIT_BYTES:
        return False, "Invalid or oversized audit file (limit: 1 MiB)."
    try:
        document = json.loads(raw.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, json.JSONDecodeError, ValueError):
        return False, "Invalid JSON audit file."
    if not isinstance(document, dict):
        return False, "Audit report must be a JSON object."
    if document.get("schema") == "fraudshield-audit-v2":
        if verify_v2_audit(document):
            return True, "Synthetic v2 report: case and report SHA-256 digests match (not proof of authenticity)."
        return False, "Synthetic v2 report is invalid or its case/report digest does not match."
    if verify_audit_report(document):
        return True, "Standard report content matches its embedded SHA-256 digest."
    return False, "Unsupported audit format, digest mismatch, or malformed audit report."
