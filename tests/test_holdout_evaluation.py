import json
import unittest
from uuid import UUID

from enterprise_core.holdout_evaluation import evaluate


class HoldoutEvaluationTests(unittest.TestCase):
    cutoff = "2026-01-01T00:00:00Z"

    def row(self, n, label, amount="10", currency="USD", flags=(False, False, False)):
        return {"id": str(UUID(int=n)), "observed_at":"2026-02-01T00:00:00Z",
                "label":label, "transaction":{"amount":amount, "currency":currency,
                **dict(zip(("country_mismatch","new_account","unusual_activity"),flags))}}

    def run_rows(self, rows):
        raw = "\n".join(json.dumps(row) for row in rows).encode()
        return evaluate(raw, self.cutoff, provenance="synthetic")

    def test_confusion_counts_and_abstention(self):
        rows = [self.row(1,True,"2000",flags=(True,True,True)),
                self.row(2,False,"2000",flags=(True,True,True)),
                self.row(3,True), self.row(4,False),
                self.row(5,True,currency="IQD"), self.row(6,False,flags=(None,False,False))]
        report = self.run_rows(rows)
        self.assertEqual(report, self.run_rows(rows))
        m = report["overall"]["policy"]
        self.assertEqual([m[k] for k in ("tp","fp","tn","fn","abstain_fraud","abstain_legitimate")],[1]*6)
        self.assertAlmostEqual(m["recall_all"],1/3)
        self.assertAlmostEqual(m["coverage"],2/3)
        self.assertEqual(m["precision"],0.5)
        self.assertEqual(report["overall"]["amount_only"]["scored"],4)
        self.assertIsNone(report["by_currency"]["IQD"]["policy"]["precision"])
        self.assertFalse(report["provenance_verified"])

    def test_reject_duplicates_and_pre_cutoff_rows(self):
        row = self.row(1,True)
        for rows in ([row,row], [row | {"observed_at":self.cutoff}], [row | {"label":1}],
                     [row | {"observed_at":"2026-02-01"}], [row | {"extra":"private"}], []):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_rows(rows)

    def test_baseline_is_distinct(self):
        r = self.run_rows([self.row(1,False,"2000")])["overall"]
        self.assertEqual(r["policy"]["tn"],1)
        self.assertEqual(r["amount_only"]["fp"],1)
