FraudShield AI

Explainable Payment Risk Intelligence — PayPal Sandbox + Machine Learning Prototype

Overview

FraudShield AI is an interactive payment risk analysis prototype developed for the PayPal AI Hackathon 2026.

It combines PayPal Sandbox API integration, rule-based risk scoring, and machine learning anomaly detection to demonstrate how suspicious transaction patterns can be identified and explained.

Live Demo: https://paypal-ai-fraudshield.streamlit.app/

Source Code: https://github.com/taleem1120-glitch/paypal-ai-fraudshield

Key Features

- PayPal Sandbox OAuth authentication
- Create test orders using the PayPal Orders API
- Retrieve Sandbox orders by order ID
- Automatically load retrieved order amounts into the analysis form
- Rule-based risk scoring from 0 to 100
- Machine learning anomaly detection using Isolation Forest
- Human-readable risk explanations and review recommendations
- Fictional transaction simulator
- Session-based transaction analysis history
- Downloadable CSV analysis reports

PayPal Integration

FraudShield AI connects to the official PayPal Sandbox API.

Implemented capabilities include:

1. Authenticate using PayPal Sandbox OAuth 2.0.
2. Create a Sandbox test order for USD 1.00.
3. Retrieve a Sandbox order using its order ID.
4. Extract the order amount and status.
5. Use the retrieved amount in the risk analysis workflow.

Sandbox orders may have a "CREATED" status. Creating an order does not mean that a payment has been approved, captured, or completed.

Risk indicators are entered manually and are not verified by PayPal.

Artificial Intelligence

The application uses an Isolation Forest machine learning model trained on synthetic transaction data.

It evaluates transaction amounts and selected risk indicators to identify statistical anomalies.

The application also calculates an independent rule-based risk score and provides explanations for the selected indicators.

Important: Statistical anomalies are not proof of fraud. The model has not been validated against real-world fraud datasets.

Technology Stack

- Python
- Streamlit
- Scikit-learn
- NumPy
- Pandas
- Requests
- PayPal Sandbox REST API
- GitHub
- Streamlit Community Cloud

Run Locally

Clone the repository:

git clone https://github.com/taleem1120-glitch/paypal-ai-fraudshield.git
cd paypal-ai-fraudshield

Install dependencies:

pip install -r requirements.txt

Configure the following Streamlit secrets using credentials from your own PayPal Developer Sandbox application:

PAYPAL_CLIENT_ID = "your_sandbox_client_id"
PAYPAL_CLIENT_SECRET = "your_sandbox_client_secret"
PAYPAL_MODE = "sandbox"

Never commit real API credentials to the public repository.

Start the application:

streamlit run app.py

Demonstration Workflow

1. Open the live application.
2. Test PayPal Sandbox authentication.
3. Create a USD 1.00 Sandbox order.
4. Copy the generated order ID.
5. Retrieve the order using the lookup form.
6. Confirm that the order amount is loaded into the transaction analysis form.
7. Select risk indicators and analyze the transaction.
8. Review the risk score, anomaly result, explanations, and recommended action.
9. Download the analysis history as a CSV file.

Limitations

FraudShield AI is a demonstration prototype.

- No real payments are processed.
- PayPal integration uses the Sandbox environment only.
- The machine learning model uses synthetic training data.
- Risk indicators are supplied manually.
- Risk scores are illustrative and are not validated fraud probabilities.
- Transaction analysis history is stored only during the Streamlit session.
- Results must not be used for real payment approval, rejection, or fraud enforcement decisions.

License

MIT License.

Hackathon

Developed as a prototype for the PayPal AI Hackathon 2026.


### Phase 1 safety and regression checks

Order lookup preserves the returned currency. Scoring currently supports **USD only**;
non-USD amounts are displayed accurately and are never converted implicitly. Multiple
purchase units and malformed amounts are rejected instead of selecting a partial total.
Editing the lookup ID, amount, or currency detaches the order. Starting another lookup
clears the old attribution even if that request fails. History captures independent
values and UTC timestamps; this is session-only provenance, not a durable audit ledger.

`scoring.py` contains the deterministic model training, rule scoring, ML scoring, and
risk decision functions. `transactions.py` handles validated money and frozen order
snapshots. The Streamlit interface retains connection testing, lookup, $1 sandbox order
creation, analysis, history CSV download, and simulation. API displays use only the
order ID, status, amount, and currency; raw customer response data is not rendered.
The sandbox client uses Python's standard HTTP library with timeouts, normal TLS
verification, blocked redirects, and sanitized errors. No payment capture is performed.
CORS and XSRF protection are explicitly enabled in `.streamlit/config.toml`.

Run regression checks with:

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m compileall -q app.py scoring.py transactions.py paypal_sandbox.py paypal_simulator.py
```

API tests use fictional data and mocked transport; they do not require credentials.
The GitHub Actions workflow runs these checks without secrets. Live sandbox integration
and browser checks require a separately configured environment. Keep credentials in
Streamlit secrets, never in source control.

## Competition 2026 development track

The stable application and its existing Devpost submission remain separate from this
unpublished development track. The branch structure is:

```text
main (stable Phase 1 baseline)
└── competition-2026 (competition baseline)
    └── phase-2-competition (reviewable development)
```

Phase 2 pull requests target **competition-2026**, never main. Creating a branch or
preparing this code does not merge, deploy, publish, or update the Devpost submission.
See [repository comparison](docs/bundle-comparison.md) for the inspected remote state
and a complete accounting of the previous bundle. Remote write access returned 403;
local branch and patch status are documented in [validation](docs/phase-2-validation.md).

### Capabilities in this development version

- Existing Sandbox connection testing, $1 test-order creation, lookup, currency
  preservation, manual analysis, simulator and CSV history remain available.
- Explainable scores retain Phase 1 weights and thresholds. Reports show each active
  and inactive rule, its contribution, input source and decision precedence. Model
  anomalies are separate alerts, with no fabricated feature-level explanations.
- Transaction observation IDs, UTC timestamps and source snapshots link reports to
  history. Each new analysis has a distinct observation ID; this is not a claim of
  a globally verified PayPal payment identity.
- Session-only cases capture explicit report attachments and evidence metadata.
  Evidence references are frozen when a report is attached; later evidence does not
  rewrite old reports. Uploaded files do not validate manually supplied risk flags.
- SHA-256 covers exact evidence bytes. Re-uploading checks a match or mismatch.
  Case edits, evidence registration/verification and report attachments produce
  hash-linked session events; exports include a consistency check and event history.
- The Sandbox boundary limits response reads to 1 MiB and exposes only validated
  order fields. Redirect blocking, timeouts, TLS verification, error sanitization,
  single-purchase-unit validation and USD-only scoring remain in force.

Cases, evidence metadata and audit events are **session-only**. Original evidence
bytes are not retained in case records; Streamlit temporarily handles uploaded files
in memory. Export before session loss. There is no case restore, authenticated actor,
access control, persistent audit ledger or externally signed trust anchor. An actor
able to rewrite the case can recompute its hashes. Hashes establish byte consistency,
not authenticity, legal chain of custody or proof of fraud.

Persistence is deliberately deferred: shared local storage on an unauthenticated,
potentially ephemeral Streamlit host would introduce retention and isolation risks.
Safe persistence needs explicit access control, retention, backup and deployment
requirements. This track does not add a database or change hosting configuration.

### Reports and evidence

Create/select a fictional case, analyze a USD transaction, then explicitly attach the
latest report. Evidence uploads require a source reference and ISO 8601 collection
time with timezone (user assertions). The limit is 10 MiB per evidence file.

Download the latest report as JSON, or the selected case as complete JSON plus separate
summary, evidence, report and audit CSVs. Schema 1.1 includes report/transaction/case
IDs, provenance, rule breakdown, alert sources, synthetic-model context, versions,
evidence references and limitations. JSON preserves text and decimal-string amounts;
CSV uses JSON for nested fields and prefixes potential spreadsheet formulas with an
apostrophe. Exported hashes use canonical UTF-8 JSON (sorted keys, compact separators,
no NaN/Infinity); file hashes use unmodified bytes. The audit check verifies event
links and current metadata/evidence/report projections, not author identity.

### Reproducible evaluation

The benchmark workspace and CLI compare rules (score >=30), anomalies, and combined
review (score >=30 **or** anomaly). They report TP/FP/TN/FN, precision, recall and
false-positive rate. Undefined ratios are null with a denominator explanation.

Synthetic data uses a sampled latent label followed by overlapping conditional
feature distributions; it does not derive labels from the scorer. Default evaluation
seed 2026 differs from training seed 42. Metrics include class balance, hash scope,
dataset SHA-256, generator/model/policy versions and runtime versions. Seeds support
repeatability in the same environment, not validation on real fraud.

Labeled imports must be UTF-8 CSV with unique required columns:

```csv
amount,currency,country_mismatch,new_account,unusual_activity,is_fraud
100.00,USD,0,0,0,0
2000.00,USD,1,1,1,1
```

Amounts must be finite/nonnegative; currency must be USD; flags/labels must be exactly
0 or 1. Additional unique columns are ignored. Limits: 10 MiB and 10,000 rows. Invalid
records are rejected before inference. Imported labels are unverified; evaluation
never retrains on them. The included `examples/labeled_evaluation.csv` is fictional,
not a real-world fraud dataset.

```sh
python -m unittest discover -s tests -v
python -m compileall -q app.py scoring.py transactions.py paypal_sandbox.py paypal_simulator.py investigations.py investigation_ui.py benchmarking.py audit.py competition_benchmark.py
python benchmarking.py --size 1000 --seed 2026 > benchmark.json
python benchmarking.py --csv examples/labeled_evaluation.csv > imported-benchmark.json
python competition_benchmark.py --sizes 1000 10000 --seeds 2026 2027 2028 --repeats 3 > competition-benchmark.json
```

The timing suite separates model fitting from repeated warm batch evaluation, checks
repeatability, and reports all samples plus min/median/max. Host timings exclude
network, UI, file I/O and data generation; they are not a service-level guarantee.

CI retains main/Phase 1 checks and adds the two competition branches and PRs targeting
competition-2026. Its Python 3.11/3.12 matrix runs tests, compilation and synthetic
benchmarks with read-only repository permissions and no secrets. Local tests mock
PayPal transport and upload objects. Live Sandbox calls, browser upload transport and
new GitHub CI runs remain unverified until actually executed.

See [architecture](docs/architecture.md), [judge demonstration](docs/demo-script.md),
[actual validation and limitations](docs/phase-2-validation.md), and
[prioritized next steps](docs/competition-next-steps.md). All scores and metrics remain
illustrative; this is not validated fraud detection or a production-ready system.
