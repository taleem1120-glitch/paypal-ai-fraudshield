import json
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audit_reporting import export_audit_json
from audit_verification import verify_uploaded_audit
from review_queue import review_rows, synthetic_reports
from scoring import train_model

PAGE = Path(__file__).resolve().parents[1] / "pages/2_Investigator_Review.py"


class StopPage(Exception):
    pass


class InvestigatorReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = synthetic_reports(train_model())

    def test_priorities_and_model_contribution(self):
        rows = review_rows(self.reports)
        self.assertEqual(rows[0]["Rule score"], 100)
        self.assertEqual(rows[-1]["Review priority"], "LOW INDICATED RISK")
        case = next(row for row in rows if float(row["Amount"]) == 850)
        self.assertEqual(case["Rule score"], 25)
        self.assertTrue(case["Model changed priority"])
        self.assertEqual(case["Review priority"], "ANOMALY DETECTED")

    def test_ties_and_original_report_integrity(self):
        tied = [r for r in self.reports if r["risk_analysis"]["rule_score"] == 45]
        self.assertEqual([r["Analysis"] for r in review_rows(tied)],
                         [r["analysis_id"] for r in tied])
        for r in self.reports:
            self.assertTrue(verify_uploaded_audit(export_audit_json(r).encode())[0])
            self.assertEqual(r["risk_analysis"]["indicator_source"], "Synthetic scenario inputs")

    def render(self, state, source, status="Open", click=None):
        ui = MagicMock()
        ui.session_state = state
        ui.radio.side_effect = [source, status]
        ui.selectbox.side_effect = lambda label, options, **kw: options[0]
        ui.button.side_effect = lambda label: label == click
        ui.stop.side_effect = StopPage
        ui.rerun.side_effect = StopPage
        with patch.dict(sys.modules, {"streamlit": ui}):
            try:
                runpy.run_path(str(PAGE))
            except StopPage:
                pass
        return ui

    def test_review_reopen_and_export_original_after_rerun(self):
        state = {"review_demo_reports": self.reports}
        self.render(state, "Synthetic demonstration", click="Mark reviewed")
        self.assertEqual(len(state["reviewed_analyses"]), 1)
        ui = self.render(state, "Synthetic demonstration", "Reviewed", "Reopen case")
        raw = ui.download_button.call_args.args[1]
        case = next(r for r in self.reports if r["analysis_id"] == json.loads(raw)["analysis_id"])
        self.assertEqual(raw, export_audit_json(case))
        self.assertFalse(state["reviewed_analyses"])

    def test_demo_never_enters_session_queue(self):
        ui = self.render({"review_demo_reports": self.reports}, "Session analyses")
        ui.dataframe.assert_not_called()
        ui.download_button.assert_not_called()
