"""Additional regression coverage for core transaction and scoring contracts."""
import unittest
import math
from decimal import Decimal
from unittest.mock import patch

from transactions import money, currency_code, parse_order, transaction_record, active_order
from scoring import rule_score, risk_decision, train_model, score_transaction
from evaluation import evaluate_synthetic_cases, demonstration_cases
from paypal_sandbox import get_paypal_sandbox_order, PayPalError


class MoneyAndCurrencyTests(unittest.TestCase):
    def test_money_decimal_exactness(self):
        self.assertEqual(money("12.30"), Decimal("12.30"))

    def test_money_rejects_nonfinite_negative_and_invalid(self):
        for value in ("NaN", "Infinity", "-0.01", "not-money"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)

    def test_currency_code_is_strict(self):
        self.assertEqual(currency_code("USD"), "USD")
        for value in ("usd", "US", "USDT", "", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                currency_code(value)


class OrderProvenanceTests(unittest.TestCase):
    def payload(self):
        return {
            "id": "ORDER-123",
            "status": "COMPLETED",
            "purchase_units": [{"amount": {"value": "15.25", "currency_code": "USD"}}],
        }

    def test_matching_single_unit_order(self):
        snap = parse_order(self.payload(), "ORDER-123")
        self.assertEqual(snap.amount, Decimal("15.25"))
        self.assertEqual(snap.currency, "USD")

    def test_mismatched_id_and_multiple_units_rejected(self):
        with self.assertRaises(ValueError):
            parse_order(self.payload(), "OTHER")
        payload = self.payload()
        payload["purchase_units"].append(payload["purchase_units"][0])
        with self.assertRaises(ValueError):
            parse_order(payload, "ORDER-123")

    def test_invalid_status_and_amount_rejected(self):
        for change in (
            {"status": "PENDING"},
            {"purchase_units": [{"amount": {"value": "NaN", "currency_code": "USD"}}]},
            {"purchase_units": [{"amount": {"value": "10", "currency_code": "usd"}}]},
        ):
            payload = self.payload()
            payload.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse_order(payload, "ORDER-123")

    def test_manual_record_does_not_inherit_unmatched_snapshot(self):
        snap = parse_order(self.payload(), "ORDER-123")
        record = transaction_record("15.26", "USD", snap)
        self.assertEqual(record["Source"], "Manual")
        self.assertEqual(record["PayPal Order ID"], "Manual")

    def test_active_order_clears_stale_attribution(self):
        state = {"order_snapshot": parse_order(self.payload(), "ORDER-123")}
        self.assertIsNone(active_order(state, amount="16.00"))
        self.assertNotIn("order_snapshot", state)


class RiskContractTests(unittest.TestCase):
    def test_rule_score_boundaries(self):
        self.assertEqual(rule_score("1000", "USD")[0], 0)
        self.assertEqual(rule_score("1000.01", "USD")[0], 25)
        self.assertEqual(rule_score("1", "USD", True, True, True)[0], 75)

    def test_non_usd_rejected_without_fx_assumption(self):
        with self.assertRaises(ValueError):
            rule_score("100", "IQD")

    def test_decision_is_review_guidance_not_payment_authorization(self):
        self.assertEqual(risk_decision(75, False)[1], "Manual review")
        self.assertEqual(risk_decision(0, True)[0], "ANOMALY DETECTED")

    def test_model_output_is_finite_and_repeatable(self):
        model = train_model()
        first = score_transaction(model, "120", "USD", False, True, False)
        second = score_transaction(model, "120", "USD", False, True, False)
        self.assertEqual(first, second)
        self.assertTrue(math.isfinite(first[3]))

    def test_synthetic_evaluation_disclaims_accuracy(self):
        summary = evaluate_synthetic_cases(train_model(), demonstration_cases())
        self.assertEqual(summary.total, len(demonstration_cases()))
        self.assertGreaterEqual(summary.agreement_rate, 0.0)
        self.assertLessEqual(summary.agreement_rate, 1.0)


class PayPalBoundaryTests(unittest.TestCase):
    def test_invalid_order_id_never_calls_network(self):
        with patch("paypal_sandbox.get_paypal_access_token") as auth:
            ok, message = get_paypal_sandbox_order("../private")
        self.assertFalse(ok)
        self.assertIn("valid Order ID", message)
        auth.assert_not_called()

    def test_empty_order_id_rejected(self):
        ok, _ = get_paypal_sandbox_order("")
        self.assertFalse(ok)

    def test_error_type_does_not_leak_raw_payload(self):
        error = PayPalError("PayPal Sandbox request failed (HTTP 500).")
        self.assertNotIn("access_token", str(error))


if __name__ == "__main__":
    unittest.main()
