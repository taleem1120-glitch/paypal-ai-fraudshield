"""Tests for bounded verification of exported audit JSON."""
import json
import unittest

from audit_reporting import create_audit_report, export_audit_json
from audit_verification import MAX_AUDIT_BYTES, verify_uploaded_audit


class AuditUploadVerificationTests(unittest.TestCase):
    def example(self):
        report = create_audit_report(
            {"Source": "Manual", "Amount": "1.00", "Currency": "USD"},
            0, False, 0.1, "LOW INDICATED RISK", "Demo only", [],
            manual_indicators={"country_mismatch": False},
        )
        return export_audit_json(report).encode("utf-8")

    def test_valid_export_passes(self):
        good, _ = verify_uploaded_audit(self.example())
        self.assertTrue(good)

    def test_changed_report_fails(self):
        report = json.loads(self.example())
        report["risk_analysis"]["rule_score"] = 99
        good, _ = verify_uploaded_audit(json.dumps(report).encode("utf-8"))
        self.assertFalse(good)

    def test_invalid_json_fails(self):
        self.assertFalse(verify_uploaded_audit(b"{")[0])

    def test_json_list_fails(self):
        self.assertFalse(verify_uploaded_audit(b"[]")[0])

    def test_oversized_file_fails(self):
        self.assertFalse(verify_uploaded_audit(b"X" * (MAX_AUDIT_BYTES + 1))[0])

    def test_empty_file_fails(self):
        self.assertFalse(verify_uploaded_audit(b"")[0])


if __name__ == "__main__":
    unittest.main()
