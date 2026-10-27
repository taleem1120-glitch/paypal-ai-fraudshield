"""Regression tests for synthetic-only risk intelligence."""
import unittest
from risk_intelligence import Scenario, SCENARIOS, explain, counterfactuals, report, verify_report

class TestRiskIntelligence(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(report(), report())
        self.assertTrue(verify_report(report()))

    def test_tampering_rejected(self):
        document = report()
        document["payload"]["cases"][0]["rule_score"] = 99
        self.assertFalse(verify_report(document))

    def test_risk_band(self):
        self.assertEqual(explain(Scenario("hi", "1200", True, True, True))["risk_band"], "high")
        self.assertEqual(explain(Scenario("lo", "25"))["rule_score"], 0)

    def test_counterfactuals(self):
        scenario = Scenario("base", "20")
        outcomes = counterfactuals(scenario)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual([x["score_if_toggled"] for x in outcomes], [30, 20, 25])

    def test_invalid_amounts(self):
        for value in ["nan", "Infinity", "-1", "1000000001", "abc"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    explain(Scenario("invalid", value))

    def test_scores_bounded_and_deterministic(self):
        for s in SCENARIOS:
            a = explain(s)
            self.assertEqual(a, explain(s))
            self.assertGreaterEqual(a["rule_score"], 0)
            self.assertLessEqual(a["rule_score"], 100)

if __name__ == "__main__":
    unittest.main()
