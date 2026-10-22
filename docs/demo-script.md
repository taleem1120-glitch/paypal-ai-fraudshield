# Proposed judge demonstration — 5 minutes

This script is a **proposal**, not an update to the existing Devpost submission.
Rehearse on the competition source locally. Do not replace the live Streamlit app or
publish new submission text without approval.

## Preparation

Install requirements, run the full suite and synthetic evaluation, then launch
`streamlit run app.py`. Prepare only fictional evidence (for example a text file
containing `fictional demonstration evidence`) and the included labeled CSV. Keep
secret files and browser developer/network tools off screen. Live Sandbox steps
require separately configured existing Sandbox credentials; they were not performed
as part of this task.

## Script

| Time | Action | Evidence-based explanation |
| --- | --- | --- |
| 0:00–0:30 | Show the prototype notice and original controls | “This is explainable payment-risk triage. Statistical anomalies are not findings of fraud. No real payment is processed.” |
| 0:30–1:15 | If available, test Sandbox connection, create the $1 test order, look it up | “We authenticated with Sandbox and created an order. CREATED does not mean approved, captured or completed. Only order identity, status, amount and currency are used.” |
| 1:15–2:00 | Analyze the retrieved USD amount; toggle a manual flag and analyze again | Show the stable rule IDs, active/inactive contributions, input sources and decision basis. “PayPal supplied these amount fields; the risk flags are our manual assertions. The model alert is independent, trained on synthetic data.” |
| 2:00–2:30 | Change the amount and analyze again | Show that the new report/history attributes the amount to Manual and uses a distinct observation ID. Previous history remains unchanged. Explain that non-USD values cannot silently be scored as USD. |
| 2:30–3:30 | Create a fictional case; register the evidence file; attach the latest analysis | Show the file's exact-byte SHA-256, user-asserted source/time, frozen evidence references and attached report. Verify the original file, then a changed copy to demonstrate match/mismatch. |
| 3:30–4:00 | Check case consistency; export case JSON and audit/report CSVs | “The session history links hashed events and checks current records. It is unsigned, session-only and is not a legal chain of custody or authenticated ledger.” |
| 4:00–4:45 | Run the default 1,000-row synthetic benchmark; optionally import the example CSV | Show TP/FP/TN/FN, precision, recall, false-positive rate and dataset hash/seed. Discuss false positives openly. “These labels are synthetic; imported labels are unverified. We never retrain on the evaluation upload.” |
| 4:45–5:00 | Show test evidence and known limitations | Cite the actual local results from validation. “Next work is independent labeled evaluation, browser/live Sandbox verification and safe storage requirements—not production readiness.” |

## Honest fallback

If Sandbox credentials or network are unavailable, state “Live Sandbox connectivity
is unavailable in this environment.” Skip the connection/order steps and use manual
fictional input and the simulator. Do not describe a simulated transaction, mocked
test, locally generated ID or offline screenshot as a live PayPal API response.

If a non-USD order is available, show its original currency and disabled analysis;
do not manufacture a live order to demonstrate this. Automated tests cover EUR/GBP/JPY
rejection and currency preservation. Never attempt approval, capture, real payments
or production endpoints during the demonstration.
