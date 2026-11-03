# PayPal AI Hackathon 2026 — Submission Readiness

This is a submission preparation checklist, **not** a record of Devpost eligibility approval. Confirm official rules and the live Devpost submission before declaring anything final.

## Verified in this repository
- [x] Public-facing README describes a prototype and its limitations
- [x] MIT open-source LICENSE file exists
- [x] GitHub Actions regression workflow is configured
- [x] Source README provides Streamlit demo URL
- [x] Sandbox + AI features are described in the technical documentation
- [x] No real payment processing is claimed

## Must be checked before the November 5 early-review opportunity
- [ ] **Public YouTube video**, under 3 minutes, with correct URL added to the Devpost submission; show actual app behavior rather than slides alone
- [ ] Video demonstrates PayPal Sandbox integration and AI analysis end-to-end, clearly distinguishing mocked/synthetic flows if live Sandbox is unavailable
- [ ] Confirm the app opens publicly in a clean browser session and that representative analysis works without private credentials
- [ ] Confirm Devpost entry points to the correct public repo and deployed app, and has complete project details
- [ ] Confirm all required participant and residence details are factually correct and compliant with official eligibility
- [ ] Record screenshots / timestamps for successful final submission review and do not assume an unverified eligibility check happened

## Known risk requiring resolution
The README states that Sandbox credentials are necessary for live PayPal API calls. The repository's mocked API tests do **not** prove that live Sandbox credentials work. If Sandbox provisioning is unavailable, the video and submission must describe the actual integration state precisely; never misrepresent synthetic flows as successful PayPal API calls. The available documentation does not establish whether a public demo video has been uploaded or linked in the submitted entry.

## Recommended presentation order
1. Ten-second problem and intended user.
2. Demonstrate how the application retrieves or prepares **synthetic** transaction context, and truthfully identify whether PayPal Sandbox is live.
3. Demonstrate explainable rules and Isolation Forest outputs, including a suspicious and a normal example.
4. Show report/audit capabilities and limitations.
5. Conclude with impact, architecture and a concise scope disclaimer.

No logo/trademark clearance or prize eligibility guarantee is made by this checklist. Review Devpost's latest official competition terms.
