# FraudShield Enterprise X pilot

## Buyer workflow

An investigation lead opens a case. An investigator submits a transaction with a stable request UUID. The service evaluates the supplied indicators, preserves the assessment bytes and returns a case UUID and SHA-256 receipt. The investigator can export those bytes, reference the receipt on a Jira issue, and present it in a Confluence report. Issue and page readers can see the reference. Keep accounts, payment data, notes, and original evidence in FraudShield.

The pilot targets review teams that already use Jira and need to reproduce a decision and hand off evidence. PayPal Fraud Protection Advanced already provides transaction review, triggered filters and risk scores. The commercial hypothesis here concerns investigation handoff and evidence retrieval. It needs buyer validation. [PayPal review workflow](https://developer.paypal.com/docs/multiparty/checkout/advanced/customize/fraud-protection/fraud-protection-advanced/review/)

## Pilot acceptance exercise

Use two synthetic organizations and separate Auth0 application configurations. Attempt a cross-organization login, repeat a transaction upload, change the content under the same key, and restore the database into an isolated instance. The target outcomes are denied access, one receipt, HTTP 409 and byte-identical export. Have a Jira user with edit access attach the receipt and a read-only user attempt a change. Have a Confluence editor insert the report and compare its digest with the exported file. Measure investigator time to retrieve a case and verify a handoff against the team's current process.

Accuracy, reduced fraud losses and willingness to pay require separate measurements. Evaluate any future detector on authorized, labeled, time-separated data. Report recall, false positives, precision and abstention by currency. The seeded anomaly model uses synthetic data. The enterprise API returns a rule score or abstains. Neither performs payment actions.

The repository carries its existing MIT license. A potential paid pilot can cover installation, integration, training and support. Pricing, support response times, retention terms, lawful processing, independent review and customer acceptance remain open. No customer contract or revenue is assumed.

## Deployment and operation

Use Python 3.11 on Linux and install `enterprise-requirements.lock`. Apply SQL files in `enterprise_core/migrations` in filename order as the migration owner. Use a distinct runtime role with no membership in the migration role, no superuser, table ownership, BYPASSRLS, database creation or schema creation privileges. Grant schema usage and the following table privileges to that role.

```sql
GRANT SELECT ON tenant_memberships TO fraudshield_app;
GRANT SELECT, INSERT, UPDATE ON investigation_cases TO fraudshield_app;
GRANT SELECT, INSERT ON case_evidence, transaction_receipts, audit_events TO fraudshield_app;
```

Provision each member's exact Auth0 subject, role and tenant UUID administratively. Configure the browser login as in AUTHENTICATION.md. Configure the API with the same issuer and tenant UUID, the Auth0 domain without scheme, organization ID, and API identifier. The API audience and web client audience are distinct. Set these on the server.

```text
FRAUDSHIELD_AUTH0_DOMAIN
FRAUDSHIELD_AUTH0_ORGANIZATION
FRAUDSHIELD_AUTH0_API_AUDIENCE
FRAUDSHIELD_OIDC_ISSUER
FRAUDSHIELD_OIDC_AUDIENCE
FRAUDSHIELD_DEFAULT_TENANT_ID
FRAUDSHIELD_DATABASE_URL
```

Run `uvicorn enterprise_core.api:create_app --factory` behind HTTPS and `streamlit run app.py` for the workbench. Terminate TLS at a trusted proxy, cap requests at 1 MiB and rate-limit requests per client. Use the psycopg driver URL (`postgresql+psycopg://`). One deployment binds one organization to one tenant. Auth0 login must include the configured organization. API access uses Auth0's official Python API SDK, pinned to a beta release. Browser sessions use Streamlit OIDC. A deployed organization's Auth0 plan and login must be verified before enabling a customer pilot.

The interactive API contract is at `/docs`. PUT a transaction to `/cases/{case_id}/transactions/{request_id}` with a stable UUID, amount string, currency, and boolean country_mismatch, new_account and unusual_activity. Unknown indicators and unsupported currencies return an abstention. The server stores the submitted values and policy version. POST an original audit file as the raw body to `/cases/{case_id}/evidence`. A content hash detects alteration against a retained receipt. It cannot identify the document's original author.

Use the registered Forge app ARI in `FRAUDSHIELD_FORGE_APP_ID`. Configure the remote and account bindings as described in [Jira verification](FORGE_VERIFICATION.md). In `forge/` run `npm ci --ignore-scripts`, `npm test` and, in an authorized developer site, `forge lint`, `forge deploy -e development` and `forge install -e development` for Jira and Confluence. First install, upgrade and uninstall need a clean-site rehearsal. Jira stores one replaceable receipt per issue through the current user's Jira permissions. The Confluence macro displays a page editor's configured receipt. Both are human-initiated references.

Take encrypted PostgreSQL backups to independently controlled storage. Restore into an isolated database with the original roles and migrations. Compare exported bytes against a retained receipt using the restricted application role. During an incident, revoke tenant memberships, preserve audit and backup snapshots and rotate affected provider credentials. To roll back the application, retain the additive tables and backup; removing the tables destroys evidence.
