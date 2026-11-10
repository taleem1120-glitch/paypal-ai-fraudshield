import unittest
from batch_triage import parse_batch, triage, verify_batch_audit
import json

HEADER = "case_id,amount_usd,country_mismatch,new_account,unusual_activity\n"
class BatchTriageTests(unittest.TestCase):
    def test_parse_and_reject_duplicate(self):
        row = "X1,100.00,no,yes,no\n"
        self.assertEqual(len(parse_batch(HEADER + row)), 1)
        with self.assertRaises(ValueError):
            parse_batch(HEADER + row + row)
    def test_reject_injection_and_bad_money(self):
        for row in ("=HYPERLINK,4,no,no,no\n", "X1,NaN,no,no,no\n",
                    "X1,1.999,no,no,no\n", "X1,20,maybe,no,no\n"):
            with self.subTest(row=row), self.assertRaises(ValueError):
                parse_batch(HEADER + row)
    def test_deterministic_audit(self):
        payload = HEADER + "B,1800,yes,yes,yes\nA,18,no,no,no\n"
        x, y = triage(payload), triage(payload)
        self.assertEqual(x, y)
        self.assertEqual(x["payload"]["findings"][0]["case_id"], "B")
        self.assertEqual(x["payload"]["findings"][0]["review_priority"], 1)
        self.assertFalse(x["payload"]["automated_payment_actions"])
    def test_audit_verifier_detects_tampering(self):
        document = triage(HEADER + "X1,12,no,yes,no\\n")
        self.assertTrue(verify_batch_audit(json.dumps(document)))
        tampered = json.loads(json.dumps(document))
        tampered["payload"]["findings"][0]["rule_score"] = 0
        self.assertFalse(verify_batch_audit(json.dumps(tampered)))
        self.assertFalse(verify_batch_audit(b"not-json"))
        self.assertFalse(verify_batch_audit("x" * 1000001))
    def test_limit(self):
        rows = "".join(f"C{i},10,no,no,no\n" for i in range(201))
        with self.assertRaises(ValueError):
            parse_batch(HEADER + rows)
if __name__ == "__main__": unittest.main()
