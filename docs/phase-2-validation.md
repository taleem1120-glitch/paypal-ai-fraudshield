# Phase 2 competition validation — 22 October 2026

## Repository and branch status

Remote main remains `4ec81c73cbbcd6e55bb7643df7bfd775e836fb18`, the merged Phase 1
baseline. The local `competition-2026` branch points to that exact commit;
`phase-2-competition` contains this development work. The previous
`dimension-x-poc-readiness` commit/bundle remains separate and unmodified.

GitHub returned 403, “Resource not accessible by integration”, when asked to create
competition-2026. No remote competition branch or Phase 2 PR was created, no code
was published and no deployment/submission was changed. The deliverable is a complete
main-based patch plus source, test logs and benchmark outputs, with application
instructions targeting **competition-2026**, not main.

## Actual tests and checks

Runtime: Python 3.12.14, Streamlit 1.66.1, scikit-learn 1.9.1, NumPy 2.5.4,
pandas 2.3.3. Requirements were installed unchanged into `/tmp/fraudshield-deps`;
commands selected them with `PYTHONPATH=/tmp/fraudshield-deps`.

| Check | Observed result |
| --- | --- |
| Recovered prior bundle suite | 44 passed in 4.356 seconds |
| Final `python -m unittest discover -s tests -v` | **58 passed in 3.997 seconds; 0 failures, errors or skips** |
| Original Phase 1 regressions | All 24 retained and passing |
| Streamlit AppTest workflows | All 5 passing; actual app reruns, mocked file uploads/API calls |
| Full mocked OAuth/lookup/create HTTP flows | Passing; no real external request |
| Compilation of all 10 application modules | Passed, exit 0 |
| Whitespace checks | Passed |
| Prior archive checksums | All entries matched |
| Remote tree comparison | All 14 main blob SHAs matched the local baseline |
| Default synthetic evaluation JSON/CSV | Passed; metrics match each other and prior bundle |
| Labeled import CLI | Passed on the included six fictional rows |
| Multi-seed/size repeatability suite | 6 configurations, 3 repetitions each; outputs identical within each configuration |

The test total comprises 24 original regressions, 20 reused investigation/benchmark/UI
tests, and 14 new Phase 2 tests. New checks cover rule contribution/source attribution,
strict booleans and model responses, observation IDs, session event consistency and
snapshot edits, evidence-reference freezing, collection-time input retention, response
byte bounds, customer field filtering, $1 order creation without capture, and repeatable
benchmark timing/reporting. Streamlit emits legacy `use_container_width` warnings;
those calls remain compatible with the original minimum dependency.

The latest existing [main CI run](https://github.com/taleem1120-glitch/paypal-ai-fraudshield/actions/runs/39586206102)
passed. **New Phase 2 CI was not run** because there is no pushed branch. The workflow
is configured for Python 3.11/3.12, read-only permissions, no secrets and synthetic-only
artifacts. Python 3.11 is not installed locally, so no local 3.11 claim is made.

## Reproducible methodology

```sh
python -m unittest discover -s tests -v
python -m compileall -q app.py scoring.py transactions.py paypal_sandbox.py paypal_simulator.py investigations.py investigation_ui.py benchmarking.py audit.py competition_benchmark.py
python benchmarking.py --size 1000 --seed 2026 > benchmark.json
python benchmarking.py --size 1000 --seed 2026 --format csv > benchmark.csv
python benchmarking.py --csv examples/labeled_evaluation.csv > imported-benchmark.json
python competition_benchmark.py --sizes 1000 10000 --seeds 2026 2027 2028 --repeats 3 > competition-benchmark.json
```

The synthetic generator samples a latent label (20% expected positives), then draws
overlapping amount/flag distributions conditional on that label. It never calls the
scoring policy to produce labels. Training remains 3,000 synthetic observations with
seed 42, Isolation Forest with 150 estimators and contamination 0.08. Evaluation uses
different seeds 2026/2027/2028. Labels do not train the model.

Rules predict review at score >=30. Anomalies predict review when the model returns
-1. Combined review uses either condition. Precision = TP/(TP+FP), recall = TP/(TP+FN),
false-positive rate = FP/(FP+TN). Zero denominators become null with an explanation.
Raw imported CSV bytes are hashed; synthetic hashes cover normalized dataset JSON.

Default evaluation has 198 synthetic positives and 802 negatives. Its SHA-256 remains
`e30d3794bc42b10ca9699840789e7cee0ef863baa2b93c6ac73089e211ebe701`.

| Policy | TP | FP | TN | FN | Precision | Recall | False-positive rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rules | 89 | 97 | 705 | 109 | 47.849462% | 44.949495% | 12.094763% |
| anomaly | 117 | 113 | 689 | 81 | 50.869565% | 59.090909% | 14.089776% |
| combined_review | 126 | 157 | 645 | 72 | 44.522968% | 63.636364% | 19.576060% |

## Local timing and seed sensitivity

The suite times one cold model fit (including lazy library import overhead), then
three warm batch evaluations per configuration with one shared trained model. Each
measurement includes validation, inference, metrics and dataset hashing; data generation,
network/UI/file I/O are excluded. Host-specific timings are not service guarantees.

Cold model-fit time in this run: **1.124425 seconds**.

| Rows | Evaluation seed | Median warm evaluation (s) | Combined precision | Combined recall | Combined false-positive rate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 2026 | 0.038219 | 44.522968% | 63.636364% | 19.576060% |
| 1000 | 2027 | 0.036243 | 45.075758% | 63.978495% | 17.813268% |
| 1000 | 2028 | 0.036241 | 50.557621% | 68.341709% | 16.604245% |
| 10000 | 2026 | 0.253409 | 47.274670% | 65.693069% | 18.546366% |
| 10000 | 2027 | 0.258676 | 44.729136% | 63.878725% | 18.671943% |
| 10000 | 2028 | 0.261786 | 45.863053% | 65.612245% | 18.880597% |

Full timing samples, per-policy confusion counts, seed, class balance, hashes and runtime
versions are in `competition-benchmark.json` in the handoff. These results do not
establish fraud accuracy on real payment data. No tuning was done to improve the
published synthetic scores. The example import's labels are fictional/unverified.

## Remaining limits and checks not performed

- No live Sandbox authentication, order lookup or creation was attempted. Existing
  credentials were not read, changed or copied; no real payment or capture occurred.
- Tests do not validate browser file-upload/download transport or the hosted app.
- Cases/evidence metadata/events are session-only. Exports cannot be restored through
  the UI. There is no durable ledger, authentication or access control. Local/shared
  database persistence is deferred pending safe isolation/retention requirements.
- Observation IDs identify analyses, not globally verified PayPal transactions.
  Evidence references are case associations, not verification of manual risk flags.
- File hashes and unsigned event links establish consistency only. A full rewrite can
  recompute all hashes; authors and timestamps are unverified. There is no trusted
  chain of custody, cryptographic signer or external audit anchor.
- No real labeled dataset, calibration, fairness/subgroup evaluation or independent
  fraud validation was available. Scores are illustrative, not probabilities; false
  positives remain material and no production-readiness claim is made.
- The existing live deployment, production endpoints, original Devpost submission,
  secret configuration, license and Streamlit security settings remain untouched.

See the separate bundle comparison, architecture, demo proposal and prioritized next
steps. Publication, any review PR, merge, deployment or submission update still
requires explicit approval; the proposed PR base is competition-2026.
