import io
import json
import unittest
import sys
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import paypal_sandbox as api
from scoring import rule_score, risk_decision, score_transaction, train_model
from transactions import money, parse_order, transaction_record, active_order


@contextmanager
def streamlit_module(fake):
    previous = sys.modules.get('streamlit')
    sys.modules['streamlit'] = fake
    try:
        yield
    finally:
        if previous is None:
            sys.modules.pop('streamlit', None)
        else:
            sys.modules['streamlit'] = previous


def order(currency='USD', value='12.34', order_id='ORDER1'):
    return {'id': order_id, 'status': 'CREATED', 'purchase_units': [
        {'amount': {'currency_code': currency, 'value': value}}]}


class CurrencyTests(unittest.TestCase):
    def test_currency_preserved(self):
        for currency in ['USD', 'EUR', 'GBP', 'JPY']:
            snapshot = parse_order(order(currency), 'ORDER1')
            self.assertEqual(snapshot.currency, currency)
            self.assertEqual(transaction_record('12.34', currency, snapshot)['Currency'], currency)

    def test_bad_amounts(self):
        for value in ['NaN', 'Infinity', '-1', None, 'bad']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)

    def test_ambiguous_or_missing_money_rejected(self):
        for payload in [{}, order(value='NaN'), order(currency=''), order(order_id='OTHER'),
                        dict(order(), purchase_units=[]),
                        dict(order(), purchase_units=order()['purchase_units'] * 2)]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_order(payload, 'ORDER1')

    def test_non_usd_not_scored(self):
        for currency in ['EUR', 'GBP', 'JPY']:
            with self.assertRaises(ValueError):
                rule_score(1500, currency)


class AttributionTests(unittest.TestCase):
    def test_snapshot_and_history_immutable(self):
        payload = order()
        snapshot = parse_order(payload, 'ORDER1')
        record = transaction_record('12.34', 'USD', snapshot)
        payload['id'] = 'OTHER'
        payload['purchase_units'][0]['amount']['value'] = '99'
        with self.assertRaises(FrozenInstanceError):
            snapshot.order_id = 'OTHER'
        self.assertEqual(record['PayPal Order ID'], 'ORDER1')
        self.assertEqual(record['Amount'], '12.34')

    def test_failed_lookup_or_edits_cannot_reuse_order(self):
        for edit in [dict(lookup_started=True), dict(requested_id='OTHER'),
                     dict(amount='99'), dict(currency='EUR')]:
            state = {'order_snapshot': parse_order(order(), 'ORDER1')}
            previous = transaction_record('12.34', 'USD', state['order_snapshot'])
            self.assertIsNone(active_order(state, **edit))
            self.assertIsNone(active_order(state, requested_id='ORDER1', amount='12.34', currency='USD'))
            self.assertEqual(previous['PayPal Order ID'], 'ORDER1')

    def test_edits_and_no_snapshot_are_manual(self):
        snapshot = parse_order(order(), 'ORDER1')
        for amount, currency, source in [('13', 'USD', snapshot), ('12.34', 'EUR', snapshot),
                                         ('12.34', 'USD', None)]:
            self.assertEqual(transaction_record(amount, currency, source)['PayPal Order ID'], 'Manual')


class ScoringTests(unittest.TestCase):
    def test_rule_boundaries(self):
        self.assertEqual(rule_score(1000, 'USD'), (0, []))
        self.assertEqual(rule_score('1000.01', 'USD')[0], 25)
        score, reasons = rule_score(1001, 'USD', True, True, True)
        self.assertEqual(score, 100)
        self.assertEqual(len(reasons), 4)

    def test_decision_precedence(self):
        for score, anomaly, expected in [(60, True, 'HIGH RISK'), (59, True, 'ANOMALY DETECTED'),
                                         (30, False, 'MEDIUM RISK'), (29, False, 'LOW INDICATED RISK')]:
            self.assertEqual(risk_decision(score, anomaly)[0], expected)

    def test_real_model_repeatable(self):
        model = train_model()
        self.assertEqual(score_transaction(model, 100, 'USD'), score_transaction(model, 100, 'USD'))

    def test_model_failure_propagates(self):
        class Broken:
            def predict(self, features):
                raise RuntimeError('model unavailable')
        with self.assertRaises(RuntimeError):
            score_transaction(Broken(), 100, 'USD')


class ApiTests(unittest.TestCase):
    def test_redirects_cannot_forward_authorization(self):
        self.assertIsNone(api._NoRedirect().redirect_request(
            None, None, 302, 'Found', {}, 'https://example.test'))

    def test_network_http_json_failures_sanitized(self):
        failures = [HTTPError('https://example.test', 401, 'SECRET CUSTOMER', {}, None),
                    URLError('SECRET CUSTOMER'), TimeoutError('SECRET CUSTOMER')]
        for failure in failures:
            with patch.object(api, 'urlopen', side_effect=failure):
                with self.assertRaises(api.PayPalError) as caught:
                    api._request('/test', {})
                self.assertNotIn('SECRET', str(caught.exception))
        for content in [b'bad SECRET', b'[]', b'null']:
            with patch.object(api, 'urlopen', return_value=io.BytesIO(content)):
                with self.assertRaises(api.PayPalError):
                    api._request('/test', {})

    def test_unexpected_errors_sanitized_on_all_operations(self):
        for operation in [api.test_paypal_connection, api.create_paypal_sandbox_order,
                          lambda: api.get_paypal_sandbox_order('ORDER1')]:
            with patch.object(api, 'get_paypal_access_token', side_effect=RuntimeError('SECRET CUSTOMER')):
                success, message = operation()
                self.assertFalse(success)
                self.assertNotIn('SECRET', message)

    def test_invalid_id_never_calls_api(self):
        with patch.object(api, 'get_paypal_access_token') as token:
            for value in ['', None, '../secrets', 'ABC?customer=1']:
                self.assertFalse(api.get_paypal_sandbox_order(value)[0])
            token.assert_not_called()

    def test_lookup_and_create_success(self):
        with patch.object(api, 'get_paypal_access_token', return_value='FAKE'), patch.object(api, '_request', return_value=order()) as request:
            self.assertTrue(api.get_paypal_sandbox_order('ORDER1')[0])
            self.assertTrue(api.create_paypal_sandbox_order()[0])
            payload = request.call_args.args[2]
            self.assertEqual(payload['purchase_units'][0]['amount']['currency_code'], 'USD')

    def test_missing_token_rejected(self):
        import sys
        from types import SimpleNamespace
        fake = SimpleNamespace(secrets={'PAYPAL_CLIENT_ID': 'fake', 'PAYPAL_CLIENT_SECRET': 'fake'})
        with streamlit_module(fake), patch.object(api, '_request', return_value={}):
            self.assertFalse(api.test_paypal_connection()[0])

    def test_missing_credentials_sanitized(self):
        import sys
        from types import SimpleNamespace
        with streamlit_module(SimpleNamespace(secrets={})):
            self.assertFalse(api.test_paypal_connection()[0])


if __name__ == '__main__':
    unittest.main()
