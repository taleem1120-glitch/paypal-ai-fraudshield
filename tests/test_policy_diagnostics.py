import unittest
from enterprise_core.policy_diagnostics import diagnostics


class PolicyDiagnosticsTests(unittest.TestCase):
    def test_full_grid_and_reproducibility(self):
        report = diagnostics()
        self.assertEqual(report, diagnostics())
        self.assertEqual(report["violations"], [])
        counts = report["counts"]
        self.assertEqual(counts["total"], 486)
        self.assertEqual(counts["scored"], 48)
        self.assertEqual(counts["abstained"], 438)
        self.assertEqual(sum(counts[k] for k in ("high", "medium", "low_indicated")), 48)
