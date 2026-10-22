"""Phase 2 validation, alert attribution, session history and mocked HTTP integration."""
from copy import deepcopy
from hashlib import sha256
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import paypal_sandbox as api
from audit import verify_case
from investigations import (add_evidence, attach_report, build_report, case_exports,
                           evidence_record, new_case, record_evidence_verification, update_case)
from scoring import rule_details, rule_score, score_transaction
from transactions import parse_order, transaction_record
from test_phase1 import order, streamlit_module


class AlertAttributionTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock()
        self.model.predict.return_value = [1]
        self.model.decision_function.return_value = [.2]

    def test_rule_catalogue_is_source_for_scores_and_reports(self):
        for amount in (0, 1000, '1000.01'):
            for bits in range(8):
                flags = tuple(bool(bits & (1 << n)) for n in range(3))
                details = rule_details(amount, 'USD', *flags)
                score, reasons = rule_score(amount, 'USD', *flags)
                report = build_report(self.model, amount, 'USD', *flags)
                self.assertEqual(score, sum(rule['contribution'] for rule in details))
                self.assertEqual(reasons, [rule['reason'] for rule in details if rule['active']])
                self.assertEqual(report['rule_score'], score)
                self.assertEqual(report['triggered_rules'], [r for r in report['rule_breakdown'] if r['active']])
                self.assertEqual(len({r['rule_id'] for r in details}), 4)

    def test_sandbox_amount_and_manual_flags_have_separate_alert_sources(self):
        snapshot = parse_order(order(value='1500'), 'ORDER1')
        report = build_report(self.model, 1500, 'USD', True, snapshot=snapshot)
        alerts = {a['alert_id']: a for a in report['alerts']}
        self.assertEqual(alerts['amount_gt_1000_usd']['source'], 'PayPal Sandbox')
        self.assertEqual(alerts['country_mismatch']['source'], 'Manual (unverified)')
        self.assertEqual(report['decision_basis'], 'rule score >= 30')
        self.assertEqual(report['transaction_id'], report['provenance']['Transaction ID'])
        changed = build_report(self.model, 1501, 'USD', snapshot=snapshot)
        self.assertEqual(changed['alerts'][0]['source'], 'Manual')

    def test_model_anomaly_does_not_invent_feature_attribution(self):
        self.model.predict.return_value = [-1]
        self.model.decision_function.return_value = [-.2]
        report = build_report(self.model, 100, 'USD')
        self.assertEqual(report['rule_score'], 0)
        self.assertEqual(report['decision_basis'], 'model anomaly')
        self.assertEqual(report['alerts'][0]['alert_id'], 'synthetic_model_anomaly')
        self.assertIsNone(report['alerts'][0]['rule_contribution'])
        self.assertFalse(report['model_context']['feature_level_attribution_available'])
        self.assertEqual(report['model_context']['training_seed'], 42)
        self.assertEqual(build_report(self.model, 1500, 'USD', True, True, True)['decision_basis'], 'rule score >= 60')

    def test_flags_invalid_model_and_non_usd_fail_before_misleading_result(self):
        for flag in ('false', 1, None):
            with self.assertRaises(ValueError):
                score_transaction(self.model, 100, 'USD', flag)
        self.model.predict.assert_not_called()
        for currency in ('EUR', 'GBP', 'JPY'):
            with self.assertRaises(ValueError):
                build_report(self.model, 100, currency)
        for predictions, decisions in [([], []), ([0], [.1]), ([1, 1], [.1]), ([1], [float('inf')])]:
            self.model.predict.return_value = predictions
            self.model.decision_function.return_value = decisions
            with self.assertRaises(ValueError):
                build_report(self.model, 100, 'USD')

    def test_transaction_identity_unique_without_order(self):
        first, second = transaction_record(100, 'USD'), transaction_record(100, 'USD')
        self.assertNotEqual(first['Transaction ID'], second['Transaction ID'])
        self.assertEqual(first['Source'], 'Manual')


class SessionAuditTests(unittest.TestCase):
    def setUp(self):
        self.case = new_case('Fictional case', 'INV-1')
        self.evidence = evidence_record(b'proof', 'proof.txt', 'fictional source', '2026-10-22T00:00:00Z')
        self.model = Mock(predict=Mock(return_value=[1]), decision_function=Mock(return_value=[.1]))

    def populate(self):
        add_evidence(self.case, self.evidence)
        attach_report(self.case, build_report(self.model, 100, 'USD'))

    def test_event_sequence_projection_and_json_round_trip(self):
        self.populate()
        update_case(self.case, 'Updated', 'INV-2', 'Fictional note', 'In review')
        self.assertTrue(record_evidence_verification(self.case, self.evidence['evidence_id'], b'proof'))
        self.assertFalse(record_evidence_verification(self.case, self.evidence['evidence_id'], b'tampered'))
        events = self.case['audit_events']
        self.assertEqual([e['sequence'] for e in events], list(range(1, 7)))
        self.assertTrue(verify_case(self.case))
        self.assertFalse(events[-1]['payload']['matched'])
        self.assertEqual(events[-1]['actor_reference'], 'INV-2')
        self.assertFalse(events[-1]['actor_verified'])
        exports = case_exports(self.case)
        saved = json.loads(exports['case.json'])
        self.assertTrue(saved['consistency_check_passed'])
        self.assertTrue(verify_case(saved))
        self.assertIn(b'evidence_verified', exports['audit.csv'])

    def test_detect_metadata_evidence_report_event_edits_and_deletions(self):
        self.populate()
        cases = []
        c = deepcopy(self.case); c['title'] = 'edited'; cases.append(c)
        c = deepcopy(self.case); c['evidence'][0]['sha256'] = '0'*64; cases.append(c)
        c = deepcopy(self.case); c['reports'][0]['rule_score'] = 99; cases.append(c)
        c = deepcopy(self.case); c['audit_events'][0]['payload']['metadata']['title'] = 'edited'; cases.append(c)
        c = deepcopy(self.case); c['audit_events'].pop(); cases.append(c)
        c = deepcopy(self.case); c['audit_events'].reverse(); cases.append(c)
        for case in cases:
            self.assertFalse(verify_case(case))
            with self.assertRaisesRegex(ValueError, 'consistency'):
                update_case(case, 'Title', 'INV', '', 'Closed')
            self.assertFalse(json.loads(case_exports(case)['case.json'])['consistency_check_passed'])

    def test_attachment_captures_existing_evidence_without_rewriting_report(self):
        self.populate()
        saved = deepcopy(self.case['reports'][0])
        refs = saved['evidence_references']
        self.assertEqual(refs, [{'evidence_id': self.evidence['evidence_id'], 'sha256': sha256(b'proof').hexdigest()}])
        add_evidence(self.case, evidence_record(b'later', 'later.txt', 'source', '2026-10-22T01:00:00Z'))
        self.assertEqual(self.case['reports'][0], saved)
        self.assertTrue(verify_case(self.case))

    def test_bad_metadata_and_duplicate_evidence_rejected(self):
        for call in (lambda: new_case('title', 'INV', float('nan')),
                     lambda: update_case(self.case, 'title', 'INV', None, 'Open'),
                     lambda: evidence_record(b'proof', 'a', 'source', '0001-01-01T00:00:00+01:00'),
                     lambda: evidence_record(b'proof', 'a', 'source', '2026-01-01T00:00:00Z', None)):
            with self.assertRaises(ValueError):
                call()
        self.assertTrue(verify_case(self.case))
        add_evidence(self.case, self.evidence)
        with self.assertRaises(ValueError):
            add_evidence(self.case, self.evidence)
        with self.assertRaises(ValueError):
            record_evidence_verification(self.case, 'unknown', b'proof')


class SandboxBoundaryIntegrationTests(unittest.TestCase):
    def test_full_mocked_oauth_lookup_and_minimal_customer_data_boundary(self):
        payload = {**order(currency='EUR'), 'payer': {'email_address': 'FICTIONAL_PRIVATE'}, 'links': ['PRIVATE']}
        payload['purchase_units'][0]['shipping'] = {'address': 'PRIVATE'}
        responses = [io.BytesIO(json.dumps({'access_token':'FICTIONAL-TOKEN'}).encode()),
                     io.BytesIO(json.dumps(payload).encode())]
        fake = SimpleNamespace(secrets={'PAYPAL_CLIENT_ID':'FAKE-ID', 'PAYPAL_CLIENT_SECRET':'FAKE-SECRET'})
        with streamlit_module(fake), patch.object(api, 'urlopen', side_effect=responses) as transport:
            success, result = api.get_paypal_sandbox_order('ORDER1')
        self.assertTrue(success)
        self.assertEqual(result['purchase_units'][0]['amount']['currency_code'], 'EUR')
        self.assertNotIn('PRIVATE', json.dumps(result))
        urls = [call.args[0].full_url for call in transport.call_args_list]
        self.assertEqual(urls, [api.PAYPAL_API+'/v1/oauth2/token', api.PAYPAL_API+'/v2/checkout/orders/ORDER1'])
        self.assertTrue(all(call.kwargs['timeout'] == 20 for call in transport.call_args_list))
        self.assertEqual(transport.call_args_list[0].args[0].data, b'grant_type=client_credentials')

    def test_mocked_creation_only_one_dollar_no_capture_and_no_customer_fields(self):
        responses = [io.BytesIO(b'{"access_token":"FAKE"}'),
                     io.BytesIO(b'{"id":"ORDER1","status":"CREATED","payer":{"email":"PRIVATE"}}')]
        fake = SimpleNamespace(secrets={'PAYPAL_CLIENT_ID':'FAKE', 'PAYPAL_CLIENT_SECRET':'FAKE'})
        with streamlit_module(fake), patch.object(api, 'urlopen', side_effect=responses) as transport:
            success, result = api.create_paypal_sandbox_order()
        self.assertTrue(success)
        self.assertEqual(result, {'id':'ORDER1','status':'CREATED'})
        request = transport.call_args_list[-1].args[0]
        self.assertEqual(request.full_url, api.PAYPAL_API+'/v2/checkout/orders')
        self.assertEqual(json.loads(request.data)['purchase_units'][0]['amount'], {'currency_code':'USD','value':'1.00'})
        self.assertFalse(any('/capture' in c.args[0].full_url for c in transport.call_args_list))

    def test_response_byte_limit_and_invalid_orders_sanitized(self):
        with patch.object(api, 'urlopen', return_value=io.BytesIO(b'x'*(api.MAX_RESPONSE_BYTES+1))):
            with self.assertRaises(api.PayPalError) as caught:
                api._request('/test', {})
        self.assertNotIn('xxx', str(caught.exception))
        for payload in ({}, order(order_id='OTHER'), order(value='NaN'), {**order(), 'status':'PRIVATE'}):
            with patch.object(api, 'get_paypal_access_token', return_value='FAKE'), patch.object(api, '_request', return_value=payload):
                success, message = api.get_paypal_sandbox_order('ORDER1')
            self.assertFalse(success)
            self.assertNotIn('PRIVATE', message)
        for payload in ({'id':'../x','status':'CREATED'}, {'id':'ORDER1','status':'PRIVATE'}):
            with patch.object(api, 'get_paypal_access_token', return_value='FAKE'), patch.object(api, '_request', return_value=payload):
                self.assertFalse(api.create_paypal_sandbox_order()[0])


class CompetitionBenchmarkTests(unittest.TestCase):
    def test_repeated_suite_reports_identical_metrics_and_timing_samples(self):
        from competition_benchmark import run_suite
        result = run_suite(sizes=(12,), seeds=(2026,), repeats=2)
        self.assertEqual(result['repeats'], 2)
        entry = result['evaluations'][0]
        self.assertEqual(entry['evaluation']['size'], 12)
        self.assertEqual(len(entry['timing_seconds']['samples']), 2)
        self.assertGreaterEqual(result['training_seconds'], 0)
        self.assertLessEqual(entry['timing_seconds']['min'], entry['timing_seconds']['median'])
        self.assertLessEqual(entry['timing_seconds']['median'], entry['timing_seconds']['max'])

    def test_invalid_suite_and_unrepeatable_outputs_are_rejected(self):
        from competition_benchmark import run_suite
        for sizes, repeats in [((0,), 1), ((10001,), 1), ((1,), 0), ((1,), 11)]:
            with self.assertRaises(ValueError):
                run_suite(sizes=sizes, repeats=repeats)
        with patch('competition_benchmark.train_model'), patch('competition_benchmark.evaluate', side_effect=[{'tp':1}, {'tp':2}]):
            with self.assertRaisesRegex(ValueError, 'inconsistent'):
                run_suite(sizes=(1,), seeds=(2026,), repeats=2)
