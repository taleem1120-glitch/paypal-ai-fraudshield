# FraudShield AI 2026 — Competition Verification Notes

This branch adds a **synthetic risk intelligence laboratory**, deliberately separated from PayPal order evidence and the existing scoring/ML prototype.

## New functionality
- Reproducible, canonical SHA-256 digest of the synthetic scenario report (integrity check, not cryptographic authenticity or durable audit trail).
- Human-readable, rule-derived reason codes for five synthetic scenarios.
- Counterfactual comparisons for three user-supplied/manual risk indicators.
- Streamlit explanation table, scenario selector, JSON download, and regression tests.

## Verification
Run:
```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m compileall -q app.py scoring.py transactions.py paypal_sandbox.py paypal_simulator.py risk_intelligence.py
```

## Honest scope and remaining release blockers
1. No verified fraud labels, production accuracy metrics, or calibration exist: *no precision/recall/F1 or fraud probability claim*.
2. PayPal OAuth/order retrieval must be tested separately using authorized Sandbox credentials held in Streamlit secrets; no real payment is captured.
3. Verify Streamlit deployment is updated from the final merged commit, then perform mobile smoke-test of every tab.
4. Capture demo/video and verify the exact Devpost submission status, judging requirements, and closing time on the official competition page.
5. Do not merge merely because standalone synthetic tests pass; CI and end-to-end UI still require validation.

## Safe demonstration story
Create a $1 Sandbox order, retrieve it, note what PayPal actually verified (ID, amount, currency, status), analyze *manually entered* risk flags in the existing tool, then open Risk Intelligence Lab to explain how rule changes alter an *educational* score. Export the tamper-evident report and demonstrate a changed payload failing digest verification.

Never represent fictional flags as PayPal merchant/account risk signals.
