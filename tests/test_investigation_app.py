"""Real Streamlit application reruns; uploads and PayPal transport are mocked."""
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from benchmarking import COLUMNS
from test_phase1 import order

APP = Path(__file__).resolve().parents[1] / 'app.py'


def element(elements, label):
    return next(item for item in elements if item.label == label)


class InvestigationAppTests(unittest.TestCase):
    def setUp(self):
        self.uploads = {}
        self.upload_patch = patch('streamlit.file_uploader', side_effect=lambda label, **kw: self.uploads.get(label))
        self.upload_patch.start()
        self.addCleanup(self.upload_patch.stop)
        self.at = AppTest.from_file(str(APP), default_timeout=20).run()
        self.assertEqual(len(self.at.exception), 0)

    def click(self, label):
        element(self.at.button, label).click().run()
        self.assertEqual(len(self.at.exception), 0)

    def create_case(self, title='Fictional investigation'):
        self.at.text_input(key='new_case_title').set_value(title)
        self.at.text_input(key='new_case_investigator').set_value('INV-TEST')
        self.click('Create investigation case')
        return self.at.session_state['investigation_cases'][self.at.session_state['selected_case']]

    def upload(self, label, data, name):
        self.uploads[label] = SimpleNamespace(size=len(data), name=name, getvalue=lambda: data)

    def test_case_creation_edit_analysis_and_exports(self):
        case = self.create_case()
        self.assertEqual(case['title'], 'Fictional investigation')
        element(self.at.selectbox, 'Case status').select('In review')
        self.click('Save case details')
        self.assertEqual(case['status'], 'In review')
        self.click('Check case consistency')
        self.assertTrue(any('consistent' in item.value for item in self.at.success))
        self.click('Analyze Transaction')
        self.click('Attach latest analysis to selected case')
        self.assertEqual(len(case['reports']), 1)
        self.assertEqual(case['reports'][0]['case_id'], case['case_id'])
        original = case['reports'][0]['inputs']['amount']
        self.at.number_input(key='transaction_amount').set_value(500).run()
        self.assertEqual(case['reports'][0]['inputs']['amount'], original)
        self.click('Attach latest analysis to selected case')
        self.assertEqual(len(case['reports']), 1)
        self.assertTrue(any('already attached' in item.value for item in self.at.warning))
        from investigations import case_exports
        exported = case_exports(case)
        self.assertEqual(json.loads(exported['case.json'])['reports'][0]['case_id'], case['case_id'])
        downloads = [item.label for item in self.at.get('download_button')]
        self.assertIn('Download case case.json', downloads)
        self.assertIn('Download case reports.csv', downloads)
        self.assertIn('Download case audit.csv', downloads)
        second = self.create_case('Second case')
        self.assertNotEqual(second['case_id'], case['case_id'])
        self.assertEqual(second['reports'], [])

    def test_evidence_upload_hash_verification_and_export(self):
        case = self.create_case()
        self.upload('Evidence file', b'fictional proof\n', 'proof.txt')
        element(self.at.text_input, 'Collected at (ISO 8601 with timezone)').set_value('2026-10-01T12:34:00+03:00')
        element(self.at.text_input, 'Evidence source reference').set_value('Fictional source')
        self.click('Record evidence metadata')
        self.assertEqual(len(case['evidence']), 1)
        self.assertEqual(case['evidence'][0]['collected_at'], '2026-10-01T09:34:00+00:00')
        self.assertEqual(case['evidence'][0]['sha256'], sha256(b'fictional proof\n').hexdigest())
        self.uploads.pop('Evidence file')
        self.upload('Re-upload original file to verify hash', b'fictional proof\n', 'renamed.txt')
        self.click('Verify evidence hash')
        self.assertTrue(any('matches' in item.value for item in self.at.success))
        self.upload('Re-upload original file to verify hash', b'changed', 'proof.txt')
        self.click('Verify evidence hash')
        self.assertTrue(any('mismatch' in item.value for item in self.at.error))
        self.assertEqual([event['event_type'] for event in case['audit_events']][-2:], ['evidence_verified', 'evidence_verified'])
        self.assertFalse(case['audit_events'][-1]['payload']['matched'])
        from investigations import case_exports
        row = next(csv.DictReader(io.StringIO(case_exports(case)['evidence.csv'].decode())))
        self.assertEqual(row['sha256'], case['evidence'][0]['sha256'])

    def test_import_evaluation_invalid_import_and_synthetic_run(self):
        data = (','.join(COLUMNS) + '\n100,USD,0,0,0,0\n2000,USD,1,1,1,1\n').encode()
        self.upload('Labeled evaluation CSV', data, 'labels.csv')
        self.click('Evaluate labeled CSV')
        result = self.at.session_state['benchmark_result']
        self.assertEqual(result['size'], 2)
        self.assertIsNone(result['evaluation_seed'])
        self.assertIn('unverified', result['dataset_source'])
        self.assertIn('Download benchmark JSON', [item.label for item in self.at.get('download_button')])
        self.upload('Labeled evaluation CSV', b'bad\n', 'bad.csv')
        self.click('Evaluate labeled CSV')
        self.assertNotIn('benchmark_result', self.at.session_state)
        self.assertTrue(any('Required unique columns' in item.value for item in self.at.error))
        element(self.at.number_input, 'Synthetic evaluation rows').set_value(30)
        self.click('Run synthetic benchmark')
        self.assertEqual(self.at.session_state['benchmark_result']['size'], 30)
        self.assertEqual(self.at.session_state['benchmark_result']['evaluation_seed'], 2026)

    def test_preserved_paypal_controls_and_attribution(self):
        with patch('paypal_sandbox.test_paypal_connection', return_value=(True, 'Mock connection successful')):
            self.click('🔗 Test PayPal Sandbox Connection')
        with patch('paypal_sandbox.create_paypal_sandbox_order', return_value=(True, {'id': 'ORDER1', 'status': 'CREATED'})):
            self.click('Create Sandbox Order ($1.00)')
        element(self.at.text_input, 'Enter PayPal Sandbox Order ID').set_value('ORDER1')
        with patch('paypal_sandbox.get_paypal_sandbox_order', return_value=(True, order())):
            self.click('Get PayPal Sandbox Order')
        self.click('Analyze Transaction')
        self.assertEqual(self.at.session_state['latest_risk_report']['provenance']['Source'], 'PayPal Sandbox')
        self.at.number_input(key='transaction_amount').set_value(99).run()
        self.click('Analyze Transaction')
        self.assertEqual(self.at.session_state['latest_risk_report']['provenance']['Source'], 'Manual')
        self.click('Generate Simulated Transaction')

    def test_failed_analysis_and_benchmark_clear_stale_results(self):
        self.click('Analyze Transaction')
        history_count = len(self.at.session_state['analysis_history'])
        with patch('investigations.score_transaction', side_effect=RuntimeError('INTERNAL SECRET')):
            self.click('Analyze Transaction')
        self.assertNotIn('latest_risk_report', self.at.session_state)
        self.assertEqual(len(self.at.session_state['analysis_history']), history_count)
        self.assertTrue(any('Analysis could not be completed' in item.value for item in self.at.error))
        self.assertFalse(any('INTERNAL SECRET' in item.value for item in self.at.error))
        self.at.run()  # Recover from the original analysis flow's st.stop().
        element(self.at.number_input, 'Synthetic evaluation rows').set_value(10)
        self.click('Run synthetic benchmark')
        with patch('investigation_ui.evaluate', side_effect=RuntimeError('INTERNAL SECRET')):
            self.click('Run synthetic benchmark')
        self.assertNotIn('benchmark_result', self.at.session_state)
        self.assertTrue(any('Benchmark could not be completed' in item.value for item in self.at.error))
        self.assertFalse(any('INTERNAL SECRET' in item.value for item in self.at.error))
