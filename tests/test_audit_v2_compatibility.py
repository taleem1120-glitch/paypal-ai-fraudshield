"""Regression tests for both audit formats and v2 nested digests."""
import copy
import hashlib
import json
import unittest

from audit_verification import verify_uploaded_audit, verify_v2_audit


def digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sample():
    case = {
        "id": "SYN-002", "amount": 9800, "velocity_1h": 9,
        "new_device": True, "cross_border": True, "linked_accounts": 5,
        "prior_disputes": 2,
    }
    assessment = {
        "score": 100, "band": "High",
        "hits": [
            {"rule": "Large value", "points": 25},
            {"rule": "High velocity", "points": 25},
            {"rule": "New device", "points": 16},
            {"rule": "Cross-border", "points": 12},
            {"rule": "Linked account cluster", "points": 12},
            {"rule": "Prior disputes", "points": 10},
        ],
        "sha256": digest(case),
    }
    report = {
        "schema": "fraudshield-audit-v2",
        "case": case, "assessment": assessment, "ai_review": None,
        "ai_provider_verified": False,
        "limitations": [
            "All cases are synthetic", "Score is heuristic, not a probability",
            "No allegation or attribution is made",
        ],
        "generated_utc": "2026-10-30T13:10:37.306342+00:00",
    }
    report["report_sha256"] = digest(report)
    return report


def upload(document):
    return verify_uploaded_audit(json.dumps(document).encode("utf-8"))


class SyntheticAuditV2Tests(unittest.TestCase):
    def test_known_sample_digests(self):
        document = sample()
        self.assertEqual(
            document["assessment"]["sha256"],
            "8380c94aca998c7402b143e9f9d61ab4897e31c35f1332586e1a18deb43a7ba4",
        )
        self.assertEqual(
            document["report_sha256"],
            "2fcccaac2469e96256d2ae861eb91941f676a87e6c967da19fa44b3246492a92",
        )
        self.assertTrue(verify_v2_audit(document))
        self.assertTrue(upload(document)[0])

    def test_changed_case_rejected(self):
        document = sample()
        document["case"]["amount"] = 900
        self.assertFalse(upload(document)[0])

    def test_changed_assessment_rejected(self):
        document = sample()
        document["assessment"]["hits"][0]["points"] = 1
        self.assertFalse(upload(document)[0])

    def test_modified_outer_hash_rejected(self):
        document = sample()
        document["report_sha256"] = "0" * 64
        self.assertFalse(upload(document)[0])

    def test_missing_inner_hash_rejected(self):
        document = sample()
        del document["assessment"]["sha256"]
        self.assertFalse(upload(document)[0])

    def test_rehashed_score_inconsistent_with_hits_rejected(self):
        document = sample()
        document["assessment"]["score"] = 0
        document["report_sha256"] = digest({
            k: v for k, v in document.items() if k != "report_sha256"
        })
        self.assertFalse(upload(document)[0])

    def test_claimed_ai_provider_review_rejected(self):
        document = sample()
        document["ai_provider_verified"] = True
        document["report_sha256"] = digest({
            k: v for k, v in document.items() if k != "report_sha256"
        })
        self.assertFalse(upload(document)[0])

    def test_oversized_rejected(self):
        self.assertFalse(verify_uploaded_audit(b"x" * (1024 * 1024 + 1))[0])

    def test_wrong_schema_rejected(self):
        document = sample()
        document["schema"] = "unknown"
        self.assertFalse(upload(document)[0])

    def test_none_and_nan_rejected(self):
        self.assertFalse(verify_uploaded_audit(b"null")[0])
        self.assertFalse(verify_uploaded_audit(b'{"x":NaN}')[0])


if __name__ == "__main__":
    unittest.main()
