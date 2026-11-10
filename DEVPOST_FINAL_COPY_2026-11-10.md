# FraudShield AI — Final Devpost Copy (November 10, 2026)

> Submission copy for manual review. This file does not confirm that Devpost fields or a video have been updated.

## Project title
FraudShield AI — Explainable PayPal Sandbox Risk Triage

## Tagline
An explainable, synthetic-data payment risk investigation workbench with PayPal Sandbox order context, analyst review queues, and audit exports.

## Inspiration
Payment fraud operations need more than opaque flags. Analysts need to understand where a signal came from, how it affected a review recommendation, and what evidence was recorded. FraudShield AI explores that workflow without processing real payments or asserting that synthetic anomaly scores establish fraud.

## What it does
FraudShield AI includes an implemented PayPal Sandbox OAuth and Orders API integration module for creating and retrieving test orders. Retrieved order IDs, statuses, USD amounts, and currencies can be brought into the analyst workflow after a successful authenticated request. A deterministic rules engine explains manually supplied indicators (country mismatch, new customer account, unusual activity, and a high-value USD threshold). Separately, an Isolation Forest trained on synthetic examples provides anomaly signals, not fraud verdicts.

The interface shows human-review recommendations and records session-only analysis history. Users can export CSV history and downloadable JSON audit reports with SHA-256 content digests. The new Analyst Workbench supports offline triage of up to 200 synthetic/manual USD cases, shows a ranked review queue with reasons, and exports a reproducible batch audit JSON. A Risk Intelligence Lab demonstrates counterfactual rule sensitivity on fictional scenarios.

The application is a prototype, not a production transaction processor: no real money is captured, the manually entered indicators are not verified by PayPal, AI is not trained on labeled production fraud data, and audit hashes are not digital signatures. Model scores must not be used to automatically approve or deny transactions.

## How we built it
Python and Streamlit for the interface; PayPal REST Sandbox OAuth 2.0 / Orders API for optional authenticated test-order context; scikit-learn Isolation Forest with deterministic synthetic training; rule-based scoring, provenance validation, bounded batch CSV parsing, and JSON audit exports. GitHub Actions runs regression tests and Python compilation checks.

## Challenges
Preventing a Sandbox-created order from being misrepresented as a captured payment; preserving currency/source attribution; rejecting malformed or non-USD scoring input; separating manually supplied indicators from authenticated order metadata; and explaining why statistical anomaly detection is not a proven fraud classifier.

## Accomplishments
Implemented PayPal Sandbox API integration code, transaction risk explanations, synthetic anomaly analysis, safeguards for order provenance, session history, JSON audit verification, and a newly merged offline batch analyst queue. Regression tests and compilation passed on the feature-branch commit. The production-hosted deployment and live credential-backed API operation require an additional on-screen smoke test before claiming final verification.

## What we learned
Trustworthy analysis requires source attribution, clear limits on machine-learning claims, reproducible explanations, safe handling of invalid transactions, and review by a human analyst.

## What's next
Measure false positives and recall using lawfully obtained labeled data, calibrate risk scores, connect authorized fraud signals, improve analyst authentication and durable audit storage, and conduct independent security and performance validation.

## Built with
PayPal Sandbox REST API, OAuth 2.0, Python, Streamlit, scikit-learn, Isolation Forest, NumPy, Pandas, GitHub Actions.

## Functional demo
https://paypal-ai-fraudshield.streamlit.app/

## Open-source repository
https://github.com/taleem1120-glitch/paypal-ai-fraudshield

## Video
Use only the new publicly viewable YouTube video URL once reviewed. The previous link should remain until the replacement is actually uploaded and checked.

## Release-blocking smoke test (manual)
1. Open the public Streamlit URL in an incognito browser; wait until the app fully loads.
2. Navigate to Analyst Workbench. Click Analyze batch. Confirm 4 scenarios, a ranked table and a JSON download.
3. On the main page, analyze the no-flags synthetic example and a high-flag example; confirm reasons and JSON export.
4. Upload the generated audit JSON to its verification control and confirm it validates.
5. Run PayPal Sandbox Test Connection, Create $1 Sandbox Order, then lookup its ID; confirm displayed ID, USD amount and CREATED status. Never show credentials in the video. If live Sandbox fails, disclose the failure and do not claim a live successful integration.
6. Confirm GitHub Actions is green for the exact main commit, not just its feature branch.
7. Confirm the video demonstrates only the actual working public version, has English audio/subtitles, is public on YouTube, and is under 3 minutes.
8. Verify that Devpost shows the correct video, repository, demo link and a final submitted status, and retain screenshots.
9. Freeze both code and submission at the competition deadline: November 12, 2026, noon PST.
