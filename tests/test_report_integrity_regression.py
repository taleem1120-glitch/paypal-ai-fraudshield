"""Offline regression checks for FraudShield report integrity.

SHA-256 detects accidental or unaccompanied modification; it is not an
authenticity signature, and anyone able to change a report can recompute it.
"""
import copy
import unittest

from audit_reporting import create_audit_report, verify_audit_report
from risk_intelligence import report as synthetic_report, verify_report as verify_synthetic


class ReportIntegrityTests(unittest.TestCase):
    def make_report(self):
        return create_audit_report(
            provenance={
                "Source": "Manual demonstration",
                "PayPal Order ID": "Manual",
                "Amount": "1.00",
                "Currency": "USD",
            },
            rule_score=75,
            anomaly=True,
            anomaly_score=-0.149,
            risk_level="HIGH RISK",
            recommended_action="Manual review",
            reasons=["Country mismatch", "New customer account"],
            manual_indicators={
                "country_mismatch": True,
                "new_account": True,
                "unusual_activity": False,
            },
        )

    def test_valid_audit_report_verifies(self):
        self.assertTrue(verify_audit_report(self.make_report()))

    def test_modified_risk_score_is_detected(self):
        document = self.make_report()
        document["risk_analysis"]["rule_score"] = 0
        self.assertFalse(verify_audit_report(document))

    def test_modified_order_id_is_detected(self):
        document = self.make_report()
        document["transaction"]["order_id"] = "ALTERED"
        self.assertFalse(verify_audit_report(document))

    def test_missing_integrity_is_rejected(self):
        document = self.make_report()
        del document["integrity"]
        self.assertFalse(verify_audit_report(document))

    def test_wrong_algorithm_is_rejected(self):
        document = self.make_report()
        document["integrity"]["algorithm"] = "MD5"
        self.assertFalse(verify_audit_report(document))

    def test_corrupt_digest_is_rejected(self):
        document = self.make_report()
        document["integrity"]["digest"] = "0" * 64
        self.assertFalse(verify_audit_report(document))

    def test_indicator_inputs_are_recorded(self):
        document = self.make_report()
        self.assertEqual(document["risk_analysis"]["manual_indicators"], {
            "country_mismatch": True,
            "new_account": True,
            "unusual_activity": False,
        })
        self.assertIn("not verified", document["risk_analysis"]["indicator_source"])
        self.assertTrue(verify_audit_report(document))

    def test_indicator_tampering_is_detected(self):
        document = self.make_report()
        document["risk_analysis"]["manual_indicators"]["country_mismatch"] = False
        self.assertFalse(verify_audit_report(document))

    def test_invalid_indicator_value_is_rejected(self):
        with self.assertRaises(ValueError):
            create_audit_report(
                {}, 0, False, 0.1, "LOW INDICATED RISK", "None", [],
                manual_indicators={"country_mismatch": "yes"},
            )

    def test_valid_synthetic_report_verifies(self):
        self.assertTrue(verify_synthetic(synthetic_report()))

    def test_modified_synthetic_case_is_detected(self):
        document = copy.deepcopy(synthetic_report())
        document["payload"]["cases"][0]["rule_score"] = 99
        self.assertFalse(verify_synthetic(document))


if __name__ == "__main__":
    unittest.main()
