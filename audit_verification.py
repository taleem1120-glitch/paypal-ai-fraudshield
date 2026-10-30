"""Bounded, local verification of exported FraudShield audit JSON files.

A matching digest detects unaccompanied changes, not signer authenticity.
"""
import json

from audit_reporting import verify_audit_report

MAX_AUDIT_BYTES = 1024 * 1024


def verify_uploaded_audit(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_AUDIT_BYTES:
        return False, "Invalid or oversized audit file (limit: 1 MiB)."
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return False, "Invalid JSON audit file."
    if not isinstance(document, dict):
        return False, "Audit report must be a JSON object."
    if not verify_audit_report(document):
        return False, "Digest mismatch or malformed audit report."
    return True, "Report content matches its embedded SHA-256 digest."
