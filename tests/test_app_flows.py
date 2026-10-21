"""Application flow tests with a minimal Streamlit harness, not browser tests."""
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from test_phase1 import order, streamlit_module

APP = Path(__file__).resolve().parents[1] / 'app.py'


class UI:
    def __init__(self):
        self.session_state = {}
        self.inputs = {}
        self.clicked = ''
        self.messages = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.messages.append((name, args))

    def spinner(self, *args):
        return self

    def columns(self, count):
        return [self] * count

    def cache_resource(self, function):
        return function

    def button(self, label, disabled=False, **kwargs):
        return label == self.clicked and not disabled

    def text_input(self, label, key=None):
        return self.session_state.get(key, '') if key else self.inputs.get(label, '')

    def number_input(self, label, key=None, **kwargs):
        return self.session_state[key]

    def checkbox(self, label):
        return self.inputs.get(label, False)


class AppFlows(unittest.TestCase):
    def setUp(self):
        self.ui = UI()
        self.model = SimpleNamespace(predict=lambda x: [1], decision_function=lambda x: [.1])

    def run_app(self, click='', response=None):
        self.ui.clicked = click
        with streamlit_module(self.ui), \
             patch('scoring.train_model', return_value=self.model), \
             patch('paypal_sandbox.get_paypal_sandbox_order', return_value=response):
            runpy.run_path(str(APP))

    def load(self, currency='USD'):
        self.ui.inputs['Enter PayPal Sandbox Order ID'] = 'ORDER1'
        self.run_app('Get PayPal Sandbox Order', (True, order(currency)))

    def analyze(self):
        self.run_app('Analyze Transaction')
        return self.ui.session_state['analysis_history'][-1]

    def test_lookup_and_history_keep_original_provenance(self):
        self.load()
        first = self.analyze()
        self.assertEqual(first['PayPal Order ID'], 'ORDER1')
        self.ui.session_state['transaction_amount'] = 99.0
        second = self.analyze()
        self.assertEqual(second['PayPal Order ID'], 'Manual')
        self.assertEqual(first['Amount'], '12.34')
        self.ui.session_state['transaction_amount'] = 12.34
        self.assertEqual(self.analyze()['PayPal Order ID'], 'Manual')

    def test_failed_lookup_clears_previous_order(self):
        self.load()
        self.run_app('Get PayPal Sandbox Order', (False, 'Network error.'))
        self.assertEqual(self.analyze()['PayPal Order ID'], 'Manual')

    def test_malformed_lookup_clears_previous_order(self):
        self.load()
        self.run_app('Get PayPal Sandbox Order', (True, {}))
        self.assertEqual(self.analyze()['PayPal Order ID'], 'Manual')

    def test_editing_lookup_id_detaches_old_order(self):
        self.load()
        self.ui.inputs['Enter PayPal Sandbox Order ID'] = 'OTHER'
        self.assertEqual(self.analyze()['PayPal Order ID'], 'Manual')

    def test_foreign_currency_is_displayed_and_scoring_disabled(self):
        self.load('EUR')
        self.assertEqual(self.ui.session_state['transaction_currency'], 'EUR')
        self.run_app('Analyze Transaction')
        self.assertNotIn('analysis_history', self.ui.session_state)
        self.ui.session_state['transaction_currency'] = 'USD'
        self.assertEqual(self.analyze()['PayPal Order ID'], 'Manual')

    def test_simulator_retains_currency(self):
        self.load('EUR')
        self.run_app('Generate Simulated Transaction')
        generated = [args[0] for name, args in self.ui.messages
                     if name == 'json' and args and args[0].get('source') == 'SIMULATED_PAYPAL']
        self.assertEqual(generated[-1]['amount']['currency_code'], 'EUR')
