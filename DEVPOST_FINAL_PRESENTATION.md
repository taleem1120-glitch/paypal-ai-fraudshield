# FraudShield AI — Final Judging Presentation & Devpost Copy

**Project:** FraudShield AI — Explainable Payment Risk Intelligence  
**Working demo:** https://paypal-ai-fraudshield.streamlit.app/  
**Source:** https://github.com/taleem1120-glitch/paypal-ai-fraudshield  
**Competition:** https://paypalaihackathon.devpost.com/

## Elevator pitch (English)

FraudShield AI makes payment-risk triage understandable. Its prototype includes PayPal Sandbox order-retrieval integration, explainable risk rules, synthetic-data anomaly detection and downloadable JSON audit exports. Live Sandbox connectivity must be verified separately before being demonstrated as working. The prototype helps demonstrate how a payment analyst might investigate unusual checkout patterns and document a human-review recommendation without automatically blocking payments.

## Inspiration

Payment fraud analysts need more than a black-box alert: they need to know which signals influenced a review recommendation. We built FraudShield AI to explore a transparent, auditable workflow around PayPal Sandbox checkouts.

## What it does

FraudShield AI authenticates to PayPal Sandbox, creates $1 test orders, retrieves an order's status, currency and amount, and imports that amount into a transaction analysis form. A simple weighted rules engine evaluates manually entered risk indicators; a separately trained Isolation Forest detects statistical anomalies relative to synthetic training data. The dashboard presents scores, explanations, review recommendations and a downloadable JSON report with an SHA-256 content digest. A risk intelligence lab shows synthetic scenarios and how toggling a risk indicator affects a rule score.

## How we built it

Python, Streamlit, PayPal REST Sandbox Orders API and OAuth 2.0, scikit-learn Isolation Forest, NumPy and Pandas. We trained the demonstration anomaly model on seeded synthetic data and added offline regression tests for currency validation, order provenance and audit integrity. GitHub hosts the public source and CI checks; Streamlit Community Cloud hosts the demo.

## Challenges we ran into

Connecting order API data to a risk workflow without confusing a created test order with a completed payment; maintaining accurate currency and source attribution after manual form changes; and communicating why an anomaly is not necessarily fraud.

## Accomplishments

Implemented PayPal Sandbox order-integration code (live credential-backed behavior requires separate verification), an interpretable risk review workflow, downloadable audit evidence, reproducible synthetic examples and automated regression gates. The interface identifies manually entered flags as manual, rather than representing them as PayPal-verified signals.

## What we learned

Transparency and provenance are as important as a model's output. A responsible payment risk tool must distinguish facts obtained through an API from investigator-supplied assumptions, and model anomalies from proven fraudulent payments.

## What's next

Obtain lawfully sourced, labeled and representative data; benchmark false positives and recall; calibrate risk decisions; integrate appropriately authorized payment signals; improve accessibility and production-grade logging, governance and safeguards. The existing prototype must not make real financial approval or blocking decisions.

## Built with

Python, Streamlit, PayPal Sandbox REST API, OAuth 2.0, scikit-learn, Isolation Forest, NumPy, Pandas, GitHub Actions.

## Suggested tags

paypal, artificial-intelligence, fraud-prevention, fintech, explainable-ai, machine-learning

## Video plan — conditional on live Sandbox access

An earlier public short-video URL was shared in outreach:
https://www.youtube.com/shorts/wGDYJ6QPWKs

This URL is **not verified as the YouTube link entered in Devpost**, nor has its duration or compliance been verified. Do not replace the submitted video until a new recording has been checked. The official rules require a public YouTube demonstration, preferably under 3 minutes, including genuine operation of the actual software.

### Safe narration (English, approximately 2 minutes)

FraudShield AI is a prototype that helps payment analysts explain why a transaction might require manual review. It combines a PayPal Sandbox integration module with an explainable rule engine and machine learning trained on synthetic data.

Here is the interactive application. Its PayPal Sandbox tools are designed to create and retrieve test orders through OAuth, without collecting or transferring real funds.

**Only if a real, authenticated Sandbox request succeeds on screen:** Here we create a one-dollar Sandbox test order and retrieve its actual order ID, currency, amount and status. CREATED is an order status, not proof of captured payment.

**If credentials or Sandbox access are unavailable instead:** Live Sandbox access is not configured in this demonstration. The order integration is implemented in code and covered by mocked regression tests, but this screen does not prove a successful PayPal API request. We therefore demonstrate the independent synthetic analysis workflow.

Next, we enter a fictional transaction and analyze it with no manually selected risk flags. The application shows a rule-based score and a separate Isolation Forest anomaly result. These are different signals and neither establishes real fraud.

Now we select illustrative indicators for a new account, country mismatch and unusual activity. These indicators are entered manually; they are not supplied or authenticated by PayPal. We repeat the analysis and inspect the risk explanation and recommended human-review action.

The app also generates a JSON audit report with a SHA-256 content digest. That digest can detect changes only when compared with a separately trusted reference; it does not certify authorship.

FraudShield AI is an educational, synthetic-only prototype. Future work includes representative labeled data, evaluation of false positives, secure authorized integrations and human oversight.

### Recording storyboard (target 2:30–2:50)
- 0:00–0:20: Problem and analyst audience, app visible
- 0:20–0:50: PayPal Sandbox panel; demonstrate **only** a real success, otherwise explain the limitation and show implemented integration
- 0:50–1:20: Synthetic transaction baseline and AI anomaly/rule outputs
- 1:20–1:55: Add manual flags; explain risk score and human-review recommendation
- 1:55–2:20: JSON audit report, integrity digest and export
- 2:20–2:40: Risk Intelligence Lab and concise closing

Record the actual running app with no credential exposure, unlicensed music or third-party trademark imagery. Never splice test/mock results to suggest a live PayPal API call.

## Submission release gate

1. Record a public YouTube video **under three minutes** showing the actual app on screen.
2. Confirm the live demo remains accessible and working; the app's PayPal Sandbox credentials remain private.
3. Verify the public repository shows the MIT LICENSE and tests passing on the intended release.
4. Paste the English project fields above into Devpost, attach GitHub, Streamlit and public YouTube URLs.
5. Submit before **November 12, 2026, 12:00 PM PST**; check Devpost displays **Submitted**, not Draft.

**Integrity note:** SHA-256 is a content checksum, not proof of authorship or secure external notarization. All fraud indicators are user-supplied and cannot be presented as PayPal-verified risk data.
