"""Reproducible evaluation of review policies; labels are never used for training."""
import argparse
import csv
from hashlib import sha256
import io
import math
from pathlib import Path
import random

from investigations import (MAX_UPLOAD_BYTES, MODEL_VERSION, SCORING_VERSION,
                           csv_export, json_export, runtime_versions)
from scoring import rule_score, train_model
from transactions import money

COLUMNS = ("amount", "currency", "country_mismatch", "new_account", "unusual_activity", "is_fraud")
MAX_ROWS = 10_000
EVALUATION_SEED = 2026
POLICY_VERSION = "review-v1-score30-or-anomaly"


def synthetic_dataset(size=1000, seed=EVALUATION_SEED):
    if not 1 <= size <= MAX_ROWS:
        raise ValueError("Dataset size must be between 1 and 10,000.")
    rng = random.Random(seed)
    rows = []
    for _ in range(size):
        # A latent class is sampled FIRST. Overlapping distributions deliberately
        # include suspicious legitimate activity and low-indicator fraud.
        label = int(rng.random() < .20)
        amount = round(rng.lognormvariate(5.5 if label else 4.5, 1.3), 2)
        rates = (.35, .45, .40) if label else (.10, .20, .08)
        flags = [int(rng.random() < rate) for rate in rates]
        rows.append(dict(zip(COLUMNS, [str(amount), "USD", *flags, label])))
    return rows


def parse_labeled_csv(data):
    if not isinstance(data, bytes) or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("CSV must be at most 10 MB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError("CSV must use UTF-8 encoding.") from None
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not set(COLUMNS).issubset(reader.fieldnames):
            raise ValueError("Required unique columns: " + ",".join(COLUMNS))
        rows = []
        for number, row in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                raise ValueError(f"Row {number}: CSV exceeds 10,000 rows.")
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("column count does not match header")
                amount = money(row["amount"])
                if row["currency"] != "USD":
                    raise ValueError("currency must be USD")
                flags = [row[key] for key in COLUMNS[2:]]
                if any(value not in {"0", "1"} for value in flags):
                    raise ValueError("flags and is_fraud must be 0 or 1")
                rows.append(dict(zip(COLUMNS, [str(amount), "USD", *map(int, flags)])))
            except ValueError as error:
                raise ValueError(f"Row {number}: {error}") from None
    except csv.Error:
        raise ValueError(f"Row {reader.line_num or 1}: malformed CSV quoting.") from None
    if not rows:
        raise ValueError("CSV must contain at least one labeled row.")
    return rows


def confusion_metrics(labels, predictions):
    if len(labels) != len(predictions) or not labels:
        raise ValueError("Nonempty labels and predictions must have equal lengths.")
    if any(value not in (0, 1) for value in [*labels, *predictions]):
        raise ValueError("Labels and predictions must be binary.")
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    ratios = {"precision": (tp, tp + fp), "recall": (tp, tp + fn),
              "false_positive_rate": (fp, fp + tn)}
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            **{key: a / b if b else None for key, (a, b) in ratios.items()},
            "undefined_metrics": [key + ": denominator is zero" for key, (_, b) in ratios.items() if not b]}


def evaluate(rows, model=None, *, source="Synthetic", seed=EVALUATION_SEED, raw_data=None):
    # Normalize and validate all rows before invoking the model.
    rows = parse_labeled_csv(csv_export(rows, list(COLUMNS)))
    model = train_model() if model is None else model
    predictions = {"rules": [], "anomaly": [], "combined_review": []}
    features = [[float(money(row["amount"])), *[row[key] for key in COLUMNS[2:5]]] for row in rows]
    # Batch inference keeps the 10,000-row UI limit practical and uses the same
    # feature order and model methods as the individual transaction scorer.
    anomalies = model.predict(features)
    decisions = model.decision_function(features)
    if len(anomalies) != len(rows) or len(decisions) != len(rows):
        raise ValueError("Model returned an invalid number of results.")
    if any(not math.isfinite(float(value)) for value in decisions) or any(value not in (-1, 1) for value in anomalies):
        raise ValueError("Model returned invalid results.")
    for row, prediction in zip(rows, anomalies):
        score, _ = rule_score(row["amount"], row["currency"],
                              *[bool(row[key]) for key in COLUMNS[2:5]])
        anomaly = bool(prediction == -1)
        predictions["rules"].append(int(score >= 30))
        predictions["anomaly"].append(int(anomaly))
        predictions["combined_review"].append(int(score >= 30 or anomaly))
    labels = [row["is_fraud"] for row in rows]
    return {"schema_version": "1.0", "dataset_source": source,
            "dataset_sha256": sha256(raw_data if raw_data is not None else json_export(rows)).hexdigest(),
            "hash_scope": "original CSV bytes" if raw_data is not None else "normalized dataset JSON bytes",
            "size": len(rows), "fraud_count": sum(labels), "legitimate_count": len(rows) - sum(labels),
            "evaluation_seed": seed, "training_seed": 42,
            "generator_version": "latent-overlap-v1" if source == "Synthetic" else None,
            "model_version": MODEL_VERSION, "scoring_version": SCORING_VERSION,
            "runtime_versions": runtime_versions(),
            "policy_version": POLICY_VERSION,
            "policies": {key: confusion_metrics(labels, values) for key, values in predictions.items()},
            "limitations": "Synthetic performance is not operational validation. Imported labels are unverified. "
                           "Predictions indicate review, not proven fraud. Evaluation data is never used to retrain."}


def benchmark_csv(result):
    meta = {key: value for key, value in result.items() if key != "policies"}
    return csv_export([{**meta, "policy": key, **metrics} for key, metrics in result["policies"].items()])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Labeled UTF-8 evaluation CSV")
    parser.add_argument("--size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=EVALUATION_SEED)
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    args = parser.parse_args()
    try:
        if args.csv:
            with args.csv.open("rb") as handle:
                data = handle.read(MAX_UPLOAD_BYTES + 1)
            result = evaluate(parse_labeled_csv(data), source="Imported labels (unverified)", seed=None, raw_data=data)
        else:
            result = evaluate(synthetic_dataset(args.size, args.seed), seed=args.seed)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    output = benchmark_csv(result) if args.format == "csv" else json_export(result)
    print(output.decode("utf-8"))


if __name__ == "__main__":
    main()
