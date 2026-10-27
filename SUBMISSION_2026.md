# PayPal AI Hackathon 2026 — Final Submission Kit

## Suggested project name
FraudShield AI — Explainable Payment Risk Intelligence

## Short description (submission-ready)
FraudShield AI is an interactive, sandbox-only payment risk intelligence prototype. It retrieves PayPal Sandbox order details, uses an Isolation Forest trained on synthetic examples to flag unusual patterns, combines that signal with explicit risk rules, and generates readable reasons and a downloadable integrity-checkable audit report. A counterfactual risk laboratory shows how changing manually entered indicators affects the risk score. It does not process money or claim verified real-world fraud detection accuracy.

## Problem / intended audience
Payment operations analysts need transparent triage tools that explain *why* a checkout appears unusual. FraudShield AI demonstrates an interpretable workflow suitable for education and future development, **not** production financial decisions.

## How PayPal and AI are used
- **PayPal REST Sandbox**: OAuth 2.0 authentication, create a $1 sandbox order, retrieve order by ID, load its exact amount, currency and status. No capture or real transfer.
- **AI**: scikit-learn Isolation Forest, deterministic training seed 42, 3,000 synthetic training rows. This detects statistical deviations from synthetic training patterns, not confirmed fraud.
- **Explainability**: four simple weighted rules, reasons, human-review suggestion, manual-indicator counterfactual comparison, session-only history, JSON audit report with SHA-256 for content-change detection.

## Three-minute demo outline (record a live run)
0:00–0:20 — Explain the audience, need for transparent risk triage and prototype limits.
0:20–0:45 — Test Sandbox OAuth and create a $1 test order; display its CREATED status.
0:45–1:10 — Retrieve that order, showing that $1 USD is loaded into the analysis form.
1:10–1:40 — Analyze no-flags baseline; explain rules vs. synthetic anomaly output.
1:40–2:05 — Enable the three manual indicators and analyze; show score 75/100, anomaly output (depending on model run) and manual-review recommendation.
2:05–2:30 — Display reasons and the JSON audit integrity digest; explain digest does **not** prove authorship.
2:30–2:50 — Open Risk Intelligence Lab and demonstrate one counterfactual change.
2:50–3:00 — Describe next steps: real labeled data, calibration, consent/security, and human oversight.

Do not edit the recording to imply that the manually supplied flags were verified by PayPal. Do not show developer credentials.

## Release verification (blocking)
- [ ] `python -m unittest discover -s tests -v` passes on the release commit.
- [ ] `python -m compileall -q app.py scoring.py transactions.py paypal_sandbox.py paypal_simulator.py audit_reporting.py evaluation.py risk_intelligence.py` succeeds.
- [ ] GitHub Actions run is green for the exact merged commit.
- [ ] Deployed Streamlit revision matches the intended commit.
- [ ] Sandbox login, create, lookup, baseline, high-risk, report export and counterfactual demo pass in the deployed application.
- [ ] Public GitHub repository has LICENSE and full instructions; secrets are not committed.
- [ ] Public YouTube video runs under 3 minutes and shows a real working demo.
- [ ] Devpost submission is explicitly saved as **Submitted**, not draft, by November 12, 2026 at 12:00 PM Pacific.

## Honest limitations
No real-world model quality metrics are supported by the synthetic samples. Rule weights and labels are illustrative, and flags are entered by the demonstrator. A SHA-256 hash detects accidental or deliberate edits unless an attacker recomputes it; it is not a digital signature or independent audit ledger. The demo processes no real payments.

## Links
- Live demo: https://paypal-ai-fraudshield.streamlit.app/
- Source: https://github.com/taleem1120-glitch/paypal-ai-fraudshield
- Hackathon: https://paypalaihackathon.devpost.com/
