"""End-to-end offline release gates: PayPal order parsing -> scoring -> audit.

No credentials, network requests, or personal information are used.
"""
import copy
import unittest

from audit_reporting import create_audit_report, verify_audit_report
from evaluation import demonstration_cases, evaluate_synthetic_cases
from risk_intelligence import SCENARIOS, counterfactuals, explain, report, verify_report
from scoring import risk_decision, rule_score, score_transaction, train_model
from transactions import active_order, parse_order, transaction_record


class ReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = train_model()

    def setUp(self):
        self.order = parse_order({
            "id": "SANDBOXDEMO123",
            "status": "CREATED",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": "1.00"}}],
        }, "SANDBOXDEMO123")

    def test_complete_high_risk_sandbox_trace(self):
        provenance = transaction_record("1.00", "USD", self.order)
        self.assertEqual(provenance["Source"], "PayPal Sandbox")
        score, reasons, anomalous, decision = score_transaction(
            self.model, 1.0, "USD", True, True, True
        )
        self.assertEqual(score, 75)
        self.assertEqual(len(reasons), 3)
        level, action = risk_decision(score, anomalous)
        self.assertEqual((level, action), ("HIGH RISK", "Manual review"))
        audit = create_audit_report(provenance, score, anomalous, decision,
                                    level, action, reasons)
        self.assertTrue(verify_audit_report(audit))
        self.assertEqual(audit["transaction"]["order_id"], "SANDBOXDEMO123")
        edited = copy.deepcopy(audit)
        edited["risk_analysis"]["rule_score"] = 0
        self.assertFalse(verify_audit_report(edited))

    def test_baseline_has_no_rule_flags(self):
        score, reasons, *_ = score_transaction(
            self.model, 1.0, "USD", False, False, False
        )
        self.assertEqual(score, 0)
        self.assertEqual(reasons, [])

    def test_currency_cannot_be_misrepresented_as_usd(self):
        with self.assertRaises(ValueError):
            score_transaction(self.model, 1.0, "EUR")
        self.assertEqual(parse_order({
            "id": "OTHERORDER", "status": "CREATED",
            "purchase_units": [{"amount": {"currency_code": "EUR", "value": "5.00"}}]
        }, "OTHERORDER").currency, "EUR")

    def test_manual_amount_change_detaches_sandbox_attribution(self):
        state = {"order_snapshot": self.order}
        self.assertIsNone(active_order(state, amount=100.0, currency="USD"))
        self.assertEqual(transaction_record(100.0, "USD", state.get("order_snapshot"))["Source"], "Manual")

    def test_order_lookup_id_change_detaches_previous_order(self):
        state = {"order_snapshot": self.order}
        self.assertIsNone(active_order(state, requested_id="DIFFERENT"))
        self.assertNotIn("order_snapshot", state)

    def test_invalid_multi_unit_order_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_order({"id": "SANDBOXDEMO123", "status": "CREATED",
                         "purchase_units": [{"amount": {"currency_code": "USD", "value": "1.00"}},
                                            {"amount": {"currency_code": "USD", "value": "2.00"}}]},
                        "SANDBOXDEMO123")

    def test_synthetic_diagnostics_are_not_fraud_accuracy(self):
        summary = evaluate_synthetic_cases(self.model, demonstration_cases())
        self.assertEqual(summary.total, 6)
        self.assertTrue(0 <= summary.agreement_rate <= 1)
        self.assertTrue(0 <= summary.anomaly_rate <= 1)

    def test_counterfactual_explanations_and_digest(self):
        self.assertEqual(len(counterfactuals(SCENARIOS[0])), 3)
        for scenario in SCENARIOS:
            self.assertLessEqual(explain(scenario)["rule_score"], 100)
        self.assertTrue(verify_report(report()))

    def test_all_rule_flags_have_explanations(self):
        score, reasons = rule_score(1500, "USD", True, True, True)
        self.assertEqual(score, 100)
        self.assertEqual(len(reasons), 4)


if __name__ == "__main__":
    unittest.main()
