# Enterprise OIDC authentication setup

Enterprise mode uses Streamlit's native OIDC login flow. Streamlit validates the
identity-provider ID token; the application then checks the verified `sub`,
`iss`, and `aud` claims against its server-side configuration and resolves an
active membership in PostgreSQL before rendering the application.

## 1. Configure the identity provider

Create an OIDC web application in your identity provider. Register the exact
redirect URI for the deployed Streamlit origin, ending in `/oauth2callback`.
For local development this is commonly `http://localhost:8501/oauth2callback`.

Configure Streamlit secrets outside Git (for example in Streamlit Community
Cloud app secrets or a local `.streamlit/secrets.toml` that is never committed):

```toml
[auth]
redirect_uri = "https://YOUR-APP-HOST/oauth2callback"
cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
client_id = "YOUR_OIDC_CLIENT_ID"
client_secret = "YOUR_OIDC_CLIENT_SECRET"
server_metadata_url = "https://YOUR_IDP/.well-known/openid-configuration"
```

Use the identity provider's actual discovery URL and exact issuer value. Do not
commit client secrets, cookie secrets, signing keys, or production credentials.

## 2. Configure the Enterprise server

Set these environment variables in the deployment environment:

- `FRAUDSHIELD_ENTERPRISE_AUTH_ENABLED=true`
- `FRAUDSHIELD_OIDC_ISSUER`: exact `iss` value issued by the provider
- `FRAUDSHIELD_OIDC_AUDIENCE`: the OIDC client/application audience
- `FRAUDSHIELD_DEFAULT_TENANT_ID`: provisioned tenant UUID
- `FRAUDSHIELD_DATABASE_URL`: PostgreSQL URL for the dedicated application role

The application role must be a non-owner, non-superuser role without
`BYPASSRLS`. Apply all PostgreSQL migrations in filename order using a controlled privileged
migration account, then grant the runtime role only the required table and
sequence permissions. Never run production migrations as the application role.

## 3. Provision membership

A trusted administrator must provision a row in `tenant_memberships` for the
exact OIDC `sub` value and tenant UUID, with one of the supported roles:
`viewer`, `analyst`, `investigator`, or `tenant_admin`.

Do not accept a browser-supplied subject or role. The initial Enterprise
deployment uses one configured default tenant; self-service tenant selection
and membership administration are intentionally not exposed.

## 4. Enable and verify

Install `requirements-enterprise.txt`, configure the identity provider and
database, then set `FRAUDSHIELD_ENTERPRISE_AUTH_ENABLED=true`. Without a valid
login, matching issuer/audience, configured tenant, database connection, and
active membership, the app stops before rendering its transaction workflow.

When the flag is false, the application displays a prominent prototype-only
warning. This mode is not suitable for public customer deployment.

Run:

```sh
python -m unittest discover -s tests -v
python -m compileall -q app.py enterprise_core
```

The automated tests verify the application-side OIDC claim gate and membership
checks using test identities and SQLite. They do not replace a live browser
login test against the organization's configured identity provider or a
production PostgreSQL security review.

The browser checks the identity token's integer issuance and expiry on each page run. At expiry it clears the Streamlit login session. Configure the identity provider to return both timestamps. Subject identifiers must match the membership record exactly, including case. Leading and trailing whitespace are rejected.
