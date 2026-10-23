"""Regression coverage for Phase 2 synthetic diagnostics and transaction provenance."""
import unittest
from unittest.mock import Mock

from evaluation import demonstration_cases, evaluate_synthetic_cases
from transactions import active_order, parse_order, transaction_record


class EvaluationTests(unittest.TestCase):
    def test_demo_cases_have_expected_schema(self):
        cases = demonstration_cases()
        self.assertEqual(len(cases), 6)
        self.assertTrue(all(len(case) == 5 and case[1] == "USD" for case in cases))

    def test_summary_is_deterministic_with_stub_model(self):
        model = Mock()
        model.predict.return_value = [1]
        model.decision_function.return_value = [0.2]
        result = evaluate_synthetic_cases(model, demonstration_cases())
        self.assertEqual(result.total, 6)
        self.assertEqual(result.flagged, 0)
        self.assertEqual(result.anomaly_rate, 0.0)
        self.assertGreaterEqual(result.agreement_rate, 0.0)
        self.assertLessEqual(result.agreement_rate, 1.0)

    def test_no_cases_or_invalid_schema_rejected(self):
        model = Mock()
        with self.assertRaises(ValueError):
            evaluate_synthetic_cases(model, [])
        with self.assertRaises(ValueError):
            evaluate_synthetic_cases(model, [(1, "USD")])

    def test_non_usd_never_misinterpreted_as_usd(self):
        model = Mock()
        with self.assertRaises(ValueError):
            evaluate_synthetic_cases(model, [(100, "EUR", False, False, False)])

    def test_order_provenance_detaches_after_edit(self):
        order = {"id": "ORDER123", "status": "CREATED", "purchase_units": [
            {"amount": {"value": "1.00", "currency_code": "USD"}}]}
        snapshot = parse_order(order, "ORDER123")
        state = {"order_snapshot": snapshot}
        self.assertEqual(transaction_record("1.00", "USD", snapshot)["Source"], "PayPal Sandbox")
        active_order(state, amount="2.00")
        self.assertIsNone(state.get("order_snapshot"))
        self.assertEqual(transaction_record("2.00", "USD", state.get("order_snapshot"))["Source"], "Manual")


if __name__ == "__main__":
    unittest.main()
