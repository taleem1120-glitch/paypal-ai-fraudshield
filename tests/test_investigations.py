import csv
from copy import deepcopy
from hashlib import sha256
import io
import json
import unittest
from unittest.mock import Mock

from investigations import (MAX_UPLOAD_BYTES, add_evidence, attach_report, build_report,
                           case_exports, csv_export, evidence_record, json_export,
                           new_case, update_case, verify_evidence)
from transactions import parse_order
from test_phase1 import order


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock()
        self.model.predict.return_value = [1]
        self.model.decision_function.return_value = [.1]
        self.case = new_case('Example', 'INV-1', 'Fictional notes')

    def report(self, snapshot=None):
        return build_report(self.model, '12.34', 'USD', True, False, False, snapshot)

    def test_case_validation_and_updates_are_atomic(self):
        for title, investigator in [('', 'INV'), ('Title', ' ')]:
            with self.assertRaises(ValueError):
                new_case(title, investigator)
        previous = deepcopy(self.case)
        for status in ('Unknown', 'Closed'):
            with self.assertRaises(ValueError):
                update_case(self.case, ' ', 'INV-2', 'changed', status)
            self.assertEqual(self.case, previous)
        update_case(self.case, 'Updated', 'INV-2', 'new note', 'In review')
        self.assertEqual(self.case['status'], 'In review')
        self.assertEqual(self.case['created_at'], previous['created_at'])
        self.assertGreaterEqual(self.case['updated_at'], previous['updated_at'])

    def test_cases_and_attached_reports_are_independent(self):
        other = new_case('Other', 'INV-2')
        report = self.report()
        attach_report(self.case, report)
        self.assertEqual(self.case['reports'][0]['case_id'], self.case['case_id'])
        self.assertIsNone(report['case_id'])
        with self.assertRaisesRegex(ValueError, 'already attached'):
            attach_report(self.case, report)
        report['inputs']['amount'] = '999'
        report['provenance']['Source'] = 'Altered'
        self.assertEqual(self.case['reports'][0]['inputs']['amount'], '12.34')
        self.assertEqual(self.case['reports'][0]['provenance']['Source'], 'Manual')
        self.assertEqual(other['reports'], [])

    def test_hash_exact_bytes_and_verification(self):
        record = evidence_record(b'abc', 'proof.txt', 'Fictional source',
                                 '2026-10-22T12:00:00+02:00', 'Description')
        self.assertEqual(record['sha256'], 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertEqual(record['byte_count'], 3)
        self.assertEqual(record['collected_at'], '2026-10-22T10:00:00+00:00')
        self.assertTrue(verify_evidence(record, b'abc'))
        self.assertFalse(verify_evidence(record, b'abc\n'))
        add_evidence(self.case, record)
        record['description'] = 'changed'
        self.assertEqual(self.case['evidence'][0]['description'], 'Description')
        self.assertNotIn('data', self.case['evidence'][0])
        self.assertEqual(evidence_record(b'', 'empty', 'source', '2026-01-01T00:00:00Z')['sha256'], sha256(b'').hexdigest())

    def test_bad_evidence_rejected(self):
        for timestamp in ('bad', '', '2026-10-22T12:00:00', None):
            with self.assertRaises(ValueError):
                evidence_record(b'a', 'a', 'source', timestamp)
        for data, filename, source in [(b'a' * (MAX_UPLOAD_BYTES + 1), 'a', 'source'),
                                       ('not bytes', 'a', 'source'), (b'a', '', 'source'), (b'a', 'a', '')]:
            with self.assertRaises(ValueError):
                evidence_record(data, filename, source, '2026-10-22T12:00:00Z')

    def test_report_explanations_and_provenance(self):
        snapshot = parse_order(order(), 'ORDER1')
        report = self.report(snapshot)
        self.assertEqual(report['rule_score'], 30)
        self.assertEqual(sum(r['weight'] for r in report['triggered_rules']), report['rule_score'])
        self.assertEqual(report['recommended_action'], 'Additional verification')
        self.assertEqual(report['provenance']['PayPal Order ID'], 'ORDER1')
        self.assertEqual(report['input_sources']['amount'], 'PayPal Sandbox')
        self.assertEqual(report['input_sources']['country_mismatch'], 'Manual (unverified)')
        self.assertEqual(self.report()['input_sources']['amount'], 'Manual')
        synthetic = build_report(self.model, 10, 'USD', source_type='Synthetic')
        self.assertEqual(set(synthetic['input_sources'].values()), {'Synthetic'})
        detached = build_report(self.model, 99, 'USD', snapshot=snapshot)
        self.assertEqual(detached['input_sources']['amount'], 'Manual')
        for flags in [(True, True, True), (False, False, False)]:
            report = build_report(self.model, 1001, 'USD', *flags)
            self.assertEqual(sum(r['weight'] for r in report['triggered_rules']), report['rule_score'])
        self.model.predict.return_value = [-1]
        self.assertEqual(self.report()['risk_level'], 'ANOMALY DETECTED')

    def test_report_invalid_values(self):
        for amount, currency, flag in [('NaN', 'USD', True), (1, 'EUR', True), (1, 'USD', 'false')]:
            with self.assertRaises(ValueError):
                build_report(self.model, amount, currency, flag)
        self.model.decision_function.return_value = [float('nan')]
        with self.assertRaises(ValueError):
            self.report()

    def test_exports_preserve_values_and_prevent_formula_execution(self):
        update_case(self.case, '=HYPERLINK("x")', ' @SUM(1)', 'comma, quote"\nUnicode Ω', 'Open')
        attach_report(self.case, self.report())
        add_evidence(self.case, evidence_record(b'proof', 'proof.txt', 'source', '2026-10-22T12:00:00Z'))
        exports = case_exports(self.case)
        saved = json.loads(exports['case.json'])
        self.assertEqual(saved['title'], self.case['title'])
        self.assertEqual(saved['reports'][0]['inputs']['amount'], '12.34')
        summary = next(csv.DictReader(io.StringIO(exports['summary.csv'].decode())))
        self.assertTrue(summary['title'].startswith("'="))
        self.assertTrue(summary['investigator_reference'].startswith("'@"))
        self.assertEqual(summary['notes'], self.case['notes'])
        report = next(csv.DictReader(io.StringIO(exports['reports.csv'].decode())))
        self.assertEqual(json.loads(report['inputs'])['amount'], '12.34')
        evidence = next(csv.DictReader(io.StringIO(exports['evidence.csv'].decode())))
        self.assertEqual(evidence['case_id'], self.case['case_id'])
        self.assertEqual(evidence['sha256'], sha256(b'proof').hexdigest())
        for value in ['=1+1', '+cmd', '-cmd', '@cmd', '\t=cmd', '\r=cmd']:
            row = next(csv.DictReader(io.StringIO(csv_export([{'v': value}]).decode())))
            self.assertEqual(row['v'], "'" + value)
        with self.assertRaises(ValueError):
            json_export({'value': float('inf')})

    def test_empty_case_exports_have_headers(self):
        exports = case_exports(self.case)
        self.assertEqual(list(csv.DictReader(io.StringIO(exports['reports.csv'].decode()))), [])
        self.assertIn(b'sha256', exports['evidence.csv'])
