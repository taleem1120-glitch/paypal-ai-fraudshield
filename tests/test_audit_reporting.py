
"""Tests for FraudShield AI audit reporting."""

import copy
import json
import unittest

from audit_reporting import (
    create_audit_report,
    verify_audit_report,
    export_audit_json,
)


def sample_report():
    provenance = {
        "Source": "Manual",
        "PayPal Order ID": "Manual",
        "PayPal Order Status": "N/A",
        "Order Retrieved At": "N/A",
        "Analyzed At": "2026-10-23T12:00:00+00:00",
        "Amount": "100.00",
        "Currency": "USD",
    }

    return create_audit_report(
        provenance=provenance,
        rule_score=45,
        anomaly=True,
        anomaly_score=-0.07,
        risk_level="ANOMALY DETECTED",
        recommended_action="Review unusual transaction",
        reasons=["New customer account"],
    )


class AuditReportingTests(unittest.TestCase):

    def test_valid_report(self):
        report = sample_report()
        self.assertTrue(verify_audit_report(report))

    def test_unique_analysis_ids(self):
        first = sample_report()
        second = sample_report()
        self.assertNotEqual(
            first["analysis_id"],
            second["analysis_id"],
        )

    def test_detect_modified_score(self):
        report = sample_report()
        modified = copy.deepcopy(report)
        modified["risk_analysis"]["rule_score"] = 90
        self.assertFalse(verify_audit_report(modified))

    def test_detect_modified_transaction(self):
        report = sample_report()
        modified = copy.deepcopy(report)
        modified["transaction"]["amount"] = "9000.00"
        self.assertFalse(verify_audit_report(modified))

    def test_invalid_digest(self):
        report = sample_report()
        report["integrity"]["digest"] = "0" * 64
        self.assertFalse(verify_audit_report(report))

    def test_json_export(self):
        report = sample_report()
        exported = export_audit_json(report)
        restored = json.loads(exported)
        self.assertTrue(verify_audit_report(restored))

    def test_invalid_input(self):
        self.assertFalse(verify_audit_report(None))
        self.assertFalse(verify_audit_report({}))


if __name__ == "__main__":
    unittest.main()
