# Prototype Baseline Audit — 2026-11-26

**Scope:** source-level inspection of the default-branch files listed below. This is not a full code review, penetration test, execution report or production-readiness certification.

## Repository baseline

- Repository: taleem1120-glitch/paypal-ai-fraudshield
- Default branch: main
- Baseline commit inspected: 41779594524b1c31f71d63b201865177ef1a90e8
- Prototype stack: Streamlit, Python, scikit-learn, NumPy, pandas and PayPal Sandbox REST API.
- Working branch created: enterprise/fraudshield-enterprise-x-foundation
- Original main branch was not modified.

## Confirmed implemented behavior

- PayPal Sandbox OAuth client-credentials authentication.
- Sandbox order creation and retrieval; the app displays a limited set of order fields.
- Rule-based scoring and Isolation Forest anomaly detection over synthetic training data.
- Session-based transaction history and investigator review state.
- CSV batch triage with bounded input (50 KB, 200 cases) and deterministic JSON digest.
- Audit JSON export and self-consistency digest verification.
- Regression tests exist for audit reporting, batch triage, risk intelligence and review queue.
- Existing CI workflow uses Python 3.11, installs requirements, runs unittest discovery and compileall.

## Confirmed limitations and release blockers for an enterprise product

| Finding | Evidence in inspected source | Severity for enterprise release |
|---|---|---|
| No durable case or transaction store | Main app and review queue use Streamlit session state | Critical capability gap |
| No authentication or tenant authorization in inspected app | No identity/tenant boundary in the inspected app and pages | Critical security gap |
| No durable evidence object lifecycle or custody service | Audit reports are local JSON exports; no object store or custody ledger | Critical capability gap |
| SHA-256 is not an authenticity/signature mechanism | audit_reporting.py explicitly documents digest limitations | High assurance gap |
| Model has no real labelled fraud validation | scoring.py trains IsolationForest on generated synthetic data | Critical model-governance gap |
| Risk flags are manually entered | app.py labels indicators as manually supplied and not PayPal verified | High data-provenance limitation |
| PayPal integration is Sandbox-only | paypal_sandbox.py uses api-m.sandbox.paypal.com | Commercial integration gap |
| USD-only scoring | scoring.py rejects non-USD values; README documents no FX conversion | Functional limitation |
| No verified multi-tenant deployment or isolation | Not present in inspected prototype | Critical security gap |
| CI workflow does not trigger on the new enterprise branch | Existing push filter lists main and phase-1-fraudshield-hardening only | CI coverage gap |

## Important distinctions

- A Sandbox order in CREATED state is not evidence of a captured or settled payment.
- Isolation Forest anomaly output is not a fraud probability or proof of fraud.
- Agreement between hand-picked rules and anomaly output is not accuracy.
- A matching embedded SHA-256 digest detects content changes relative to that digest; it does not authenticate the author, acquisition event or source.
- The inspection does not establish that every repository file, dependency or deployment secret has been reviewed.

## Immediate engineering actions

1. Enable existing regression workflow on the isolated enterprise branch.
2. Run baseline tests and capture the actual workflow result before changing application logic.
3. Complete test inventory and review uncovered modules.
4. Implement commercial core behind explicit domain/API boundaries, preserving the prototype as reference.
5. Add identity, tenant isolation, durable storage, evidence custody and audit controls before any real customer data is accepted.
