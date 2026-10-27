# FraudShield AI — Final Judging Presentation & Devpost Copy

**Project:** FraudShield AI — Explainable Payment Risk Intelligence  
**Working demo:** https://paypal-ai-fraudshield.streamlit.app/  
**Source:** https://github.com/taleem1120-glitch/paypal-ai-fraudshield  
**Competition:** https://paypalaihackathon.devpost.com/

## Elevator pitch (English)

FraudShield AI makes payment-risk triage understandable. It combines live PayPal Sandbox order retrieval with explainable risk rules, synthetic-data anomaly detection and verifiable JSON audit exports. The prototype helps demonstrate how a payment analyst might investigate unusual checkout patterns and document a human-review recommendation without automatically blocking payments.

## Inspiration

Payment fraud analysts need more than a black-box alert: they need to know which signals influenced a review recommendation. We built FraudShield AI to explore a transparent, auditable workflow around PayPal Sandbox checkouts.

## What it does

FraudShield AI authenticates to PayPal Sandbox, creates $1 test orders, retrieves an order's status, currency and amount, and imports that amount into a transaction analysis form. A simple weighted rules engine evaluates manually entered risk indicators; a separately trained Isolation Forest detects statistical anomalies relative to synthetic training data. The dashboard presents scores, explanations, review recommendations and a downloadable JSON report with an SHA-256 content digest. A risk intelligence lab shows synthetic scenarios and how toggling a risk indicator affects a rule score.

## How we built it

Python, Streamlit, PayPal REST Sandbox Orders API and OAuth 2.0, scikit-learn Isolation Forest, NumPy and Pandas. We trained the demonstration anomaly model on seeded synthetic data and added offline regression tests for currency validation, order provenance and audit integrity. GitHub hosts the public source and CI checks; Streamlit Community Cloud hosts the demo.

## Challenges we ran into

Connecting order API data to a risk workflow without confusing a created test order with a completed payment; maintaining accurate currency and source attribution after manual form changes; and communicating why an anomaly is not necessarily fraud.

## Accomplishments

A demonstrated end-to-end PayPal Sandbox integration, an interpretable risk review workflow, downloadable audit evidence, reproducible synthetic examples and automated regression gates. The interface identifies manually entered flags as manual, rather than representing them as PayPal-verified signals.

## What we learned

Transparency and provenance are as important as a model's output. A responsible payment risk tool must distinguish facts obtained through an API from investigator-supplied assumptions, and model anomalies from proven fraudulent payments.

## What's next

Obtain lawfully sourced, labeled and representative data; benchmark false positives and recall; calibrate risk decisions; integrate appropriately authorized payment signals; improve accessibility and production-grade logging, governance and safeguards. The existing prototype must not make real financial approval or blocking decisions.

## Built with

Python, Streamlit, PayPal Sandbox REST API, OAuth 2.0, scikit-learn, Isolation Forest, NumPy, Pandas, GitHub Actions.

## Suggested tags

paypal, artificial-intelligence, fraud-prevention, fintech, explainable-ai, machine-learning

## Voice-over script (approx. 240 words, target under 2m45s with pauses)

Payment risk alerts are useful only when people can understand and review them. FraudShield AI is our explainable payment risk intelligence prototype.

First, we connect securely to PayPal Sandbox. We create a one-dollar test order and retrieve its actual order ID, amount, currency, and status. The order is created in the test environment; no real money moves.

Now we analyze that order. With no manually entered warning signs, the rules give a low score. The machine learning model independently checks whether the pattern looks unusual compared with synthetic training examples.

Next, we add three illustrative warning signs: a country mismatch, a new customer account, and unusual activity. The rules now produce a score of seventy-five out of one hundred, recommending human review. The model also flags a statistical anomaly in our demonstration.

The app explains which indicators caused the rule score. It creates a downloadable audit record with a SHA-two-fifty-six digest that can detect later changes to the report.

We also include a risk intelligence lab to compare synthetic scenarios and explore how individual indicators change a risk score.

FraudShield AI is not a production fraud detector. The warning signs are manually entered, the model uses synthetic data, and the scores are not validated fraud probabilities. Our goal is to demonstrate transparent, human-centered payment risk analysis using PayPal and AI.

## Recording storyboard

- **0:00–0:20** app title and introduction; show the problem and audience.
- **0:20–0:45** click Test PayPal Sandbox Connection; show success.
- **0:45–1:15** create $1 Sandbox Order; copy ID, retrieve order; show amount 1.00 USD and CREATED status.
- **1:15–1:45** keep three flags unchecked; Analyze Transaction; show score 0 and baseline.
- **1:45–2:15** check all three flags; Analyze Transaction; show score 75 and review recommendation.
- **2:15–2:35** scroll to reasons and Audit Report; show downloadable JSON and digest.
- **2:35–2:45** open synthetic Risk Intelligence Lab, show counterfactuals and closing message.

Narration can be replaced by accurate English captions. Record the actual functioning app rather than fabricated screenshots, and hide tokens or credentials. Use original narration and no copyrighted music.

## Submission release gate

1. Record a public YouTube video **under three minutes** showing the actual app on screen.
2. Confirm the live demo remains accessible and working; the app's PayPal Sandbox credentials remain private.
3. Verify the public repository shows the MIT LICENSE and tests passing on the intended release.
4. Paste the English project fields above into Devpost, attach GitHub, Streamlit and public YouTube URLs.
5. Submit before **November 12, 2026, 12:00 PM PST**; check Devpost displays **Submitted**, not Draft.

**Integrity note:** SHA-256 is a content checksum, not proof of authorship or secure external notarization. All fraud indicators are user-supplied and cannot be presented as PayPal-verified risk data.
