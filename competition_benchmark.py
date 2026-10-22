"""Synthetic competition evaluation and timings; no operational performance claim."""
import argparse
from statistics import median
from time import perf_counter

from benchmarking import evaluate, synthetic_dataset
from investigations import json_export, runtime_versions
from scoring import train_model


def run_suite(sizes=(1000, 10000), seeds=(2026, 2027, 2028), repeats=3):
    if not 1 <= repeats <= 10 or not sizes or not seeds:
        raise ValueError('Choose 1–10 repeats and at least one size and seed.')
    if any(not 1 <= size <= 10000 for size in sizes):
        raise ValueError('Sizes must be between 1 and 10,000.')
    start = perf_counter()
    model = train_model()
    training_seconds = perf_counter() - start
    evaluations = []
    for size in sizes:
        for seed in seeds:
            rows = synthetic_dataset(size, seed)
            durations = []
            expected = None
            for _ in range(repeats):
                start = perf_counter()
                result = evaluate(rows, model, seed=seed)
                durations.append(perf_counter() - start)
                if expected is not None and result != expected:
                    raise ValueError('Identical dataset/model produced inconsistent evaluation outputs.')
                expected = result
            evaluations.append({'evaluation': expected, 'timing_seconds': {
                'samples': durations, 'min': min(durations), 'median': median(durations), 'max': max(durations)}})
    return {'method': 'One synthetic model fit; repeated warm batch evaluation including validation, hashing and metrics. '
                      'Dataset generation, UI/network and export I/O excluded from timed evaluations.',
            'training_seconds': training_seconds, 'repeats': repeats, 'runtime_versions': runtime_versions(),
            'limitations': 'Host-specific local timings; seeds and metrics do not establish real-world fraud detection performance.',
            'evaluations': evaluations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000])
    parser.add_argument('--seeds', type=int, nargs='+', default=[2026, 2027, 2028])
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    try:
        result = run_suite(args.sizes, args.seeds, args.repeats)
    except ValueError as error:
        parser.error(str(error))
    print(json_export(result).decode('utf-8'))


if __name__ == '__main__':
    main()
