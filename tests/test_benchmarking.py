import json
import unittest
from unittest.mock import Mock, patch

from benchmarking import (COLUMNS, MAX_ROWS, benchmark_csv, confusion_metrics,
                          evaluate, parse_labeled_csv, synthetic_dataset)
from investigations import MAX_UPLOAD_BYTES, csv_export
from scoring import score_transaction, train_model

HEADER = ','.join(COLUMNS) + '\n'


class BenchmarkTests(unittest.TestCase):
    def test_known_confusion_matrix(self):
        metrics = confusion_metrics([1, 1, 1, 0, 0], [1, 1, 0, 1, 0])
        self.assertEqual([metrics[key] for key in ('tp', 'fp', 'tn', 'fn')], [2, 1, 1, 1])
        self.assertAlmostEqual(metrics['precision'], 2/3)
        self.assertAlmostEqual(metrics['recall'], 2/3)
        self.assertEqual(metrics['false_positive_rate'], .5)

    def test_undefined_denominators(self):
        no_alerts = confusion_metrics([0, 0], [0, 0])
        self.assertIsNone(no_alerts['precision'])
        self.assertIsNone(no_alerts['recall'])
        self.assertEqual(no_alerts['false_positive_rate'], 0)
        no_negative = confusion_metrics([1, 1], [1, 1])
        self.assertIsNone(no_negative['false_positive_rate'])
        self.assertEqual(len(no_negative['undefined_metrics']), 1)
        for labels, predictions in [([], []), ([1], []), ([2], [1])]:
            with self.assertRaises(ValueError):
                confusion_metrics(labels, predictions)

    def test_generator_independent_repeatable_and_overlapping(self):
        with patch('benchmarking.rule_score', side_effect=AssertionError('labels cannot call scorer')):
            rows = synthetic_dataset()
        self.assertEqual(rows, synthetic_dataset())
        self.assertNotEqual(rows, synthetic_dataset(seed=2027))
        self.assertEqual(len(rows), 1000)
        # Both label classes share identical flag combinations and amount ranges.
        flags = lambda row: tuple(row[key] for key in COLUMNS[2:5])
        self.assertTrue({flags(r) for r in rows if r['is_fraud']} & {flags(r) for r in rows if not r['is_fraud']})
        for size in (0, MAX_ROWS + 1):
            with self.assertRaises(ValueError):
                synthetic_dataset(size)

    def test_csv_validation_and_row_errors(self):
        valid = (HEADER + '12.34,USD,0,1,0,1\n').encode()
        self.assertEqual(parse_labeled_csv(valid)[0]['is_fraud'], 1)
        self.assertEqual(parse_labeled_csv(b'\xef\xbb\xbf' + valid), parse_labeled_csv(valid))
        for row in ['NaN,USD,0,1,0,1', '-1,USD,0,1,0,1', '1,EUR,0,1,0,1',
                    '1,USD,true,1,0,1', '1,USD,0,1,0,2', '1,USD,0,1,0',
                    '1,USD,0,1,0,1,extra']:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, 'Row 2:'):
                parse_labeled_csv((HEADER + row + '\n').encode())
        for data in [b'wrong\n1\n', HEADER.encode(), b'\xff',
                     (HEADER + '"unterminated').encode(), b'a' * (MAX_UPLOAD_BYTES + 1),
                     (HEADER + '1,USD,0,0,0,0\n' * (MAX_ROWS + 1)).encode(),
                     (HEADER.rstrip() + ',amount\n1,USD,0,0,0,1,1\n').encode()]:
            with self.assertRaises(ValueError):
                parse_labeled_csv(data)

    def test_policies_known_results_and_no_training_on_import(self):
        data = (HEADER + '100,USD,0,0,0,0\n100,USD,1,0,0,1\n100,USD,0,0,0,1\n').encode()
        model = Mock()
        model.predict.return_value = [1, 1, -1]
        model.decision_function.return_value = [.1, .1, -.1]
        result = evaluate(parse_labeled_csv(data), model, source='Imported labels (unverified)', seed=None, raw_data=data)
        self.assertEqual(result['policies']['rules']['recall'], .5)
        self.assertEqual(result['policies']['anomaly']['recall'], .5)
        self.assertEqual(result['policies']['combined_review']['recall'], 1)
        self.assertEqual(result['size'], 3)
        self.assertEqual(result['fraud_count'], 2)
        self.assertIsNone(result['evaluation_seed'])
        model.fit.assert_not_called()
        from hashlib import sha256
        self.assertEqual(result['dataset_sha256'], sha256(data).hexdigest())
        self.assertIn(b'combined_review', benchmark_csv(result))
        model.predict.return_value = [1]
        with self.assertRaises(ValueError):
            evaluate(parse_labeled_csv(data), model)

    def test_batch_matches_real_individual_scoring_and_is_reproducible(self):
        model = train_model()
        rows = synthetic_dataset(24)
        result = evaluate(rows, model)
        self.assertEqual(result, evaluate(rows, model))
        predicted = []
        for row in rows:
            score, _, anomaly, _ = score_transaction(model, row['amount'], 'USD',
                                                     *[bool(row[key]) for key in COLUMNS[2:5]])
            predicted.append(int(score >= 30 or anomaly))
        expected = confusion_metrics([row['is_fraud'] for row in rows], predicted)
        self.assertEqual(result['policies']['combined_review'], expected)

    def test_reject_before_inference_and_nonfinite_model(self):
        model = Mock()
        with self.assertRaises(ValueError):
            evaluate([dict(zip(COLUMNS, ['NaN', 'USD', 0, 0, 0, 1]))], model)
        model.predict.assert_not_called()
        model.predict.return_value = [1]
        model.decision_function.return_value = [float('nan')]
        with self.assertRaises(ValueError):
            evaluate(synthetic_dataset(1), model)
