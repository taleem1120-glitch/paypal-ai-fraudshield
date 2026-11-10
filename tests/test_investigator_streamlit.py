"""Exercise real Streamlit widgets when the application dependencies are installed."""
import importlib.util
import json
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Streamlit runtime required")
class InvestigatorStreamlitTests(unittest.TestCase):
    def test_demo_review_cycle(self):
        from streamlit.testing.v1 import AppTest

        page = Path(__file__).resolve().parents[1] / "pages/2_Investigator_Review.py"
        app = AppTest.from_file(str(page), default_timeout=30).run()
        self.assertFalse(app.exception)
        app.radio[0].set_value("Synthetic demonstration").run()
        self.assertFalse(app.exception)
        originals = json.dumps(app.session_state["review_demo_reports"], sort_keys=True)
        self.assertEqual(len(app.selectbox[0].options), 6)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox[0].options), 5)
        app.radio[1].set_value("Reviewed").run()
        self.assertEqual(len(app.selectbox[0].options), 1)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["reviewed_analyses"])
        self.assertEqual(originals, json.dumps(app.session_state["review_demo_reports"], sort_keys=True))
