# FraudShield Enterprise X — Target Architecture

Status: proposed baseline; not yet implemented or certified.

## Product boundaries

Two deliverables share documented contracts, not runtime assumptions:
1. Commercial core: independently deployable web application and API, useful without Atlassian or PayPal credentials.
2. Codegeist Forge app: separately packaged Atlassian integration. Forge is an integration surface, not the authoritative database or risk engine.

The existing Streamlit app remains the prototype and reference implementation until parity, migration and regression criteria are met. Do not describe prototype functions as production capabilities.

## Logical components

- Identity and tenant boundary: authentication, membership, roles, permission checks, tenant-scoped queries and session lifecycle.
- Case service: lifecycle, assignment, status, notes, links and investigation timeline.
- Transaction intake: validated adapters, idempotency, schema validation, currency-aware money and source provenance.
- Risk engine: versioned deterministic rules, model interface, reason codes, thresholds and abstention. No automated payment decisions.
- Evidence service: immutable object versions, SHA-256 content digest, acquisition metadata, custody events, access log and retention policy. A digest alone does not prove authenticity.
- Audit service: append-only event interface, actor, tenant, timestamp, action, object reference, correlation ID and integrity verification. Tamper resistance requires protected storage/keys and independent controls.
- Reporting service: reproducible case and management reports with provenance and limitations.
- Integration adapters: PayPal Sandbox initially; Jira/Confluence for Forge. Each adapter is optional and isolated.
- Operations: structured logs, metrics, traces, health checks, backup/restore and controlled migrations.

## Deployment shape

Start with a modular monolith to reduce operational burden while preserving bounded modules and stable interfaces:
- React + TypeScript client.
- FastAPI service with typed request/response schemas.
- PostgreSQL authoritative transactional store.
- S3-compatible object storage for evidence binaries, with versioning and retention controls.
- Background worker only for durable asynchronous work; introduce a queue only when measured need justifies it.
- TLS termination and deployment-managed secrets.
- Containerized local/test deployment; production deployment profiles documented separately.

No Kubernetes, Kafka or Redis requirement is assumed. Add infrastructure only when workload or operations evidence supports it.

## Data and trust boundaries

- Every tenant-owned row carries a tenant identifier and is accessed through tenant-scoped service methods.
- Tenant isolation is enforced server-side, never by UI filtering. PostgreSQL row-level security is a defense-in-depth candidate and must be tested with the chosen connection-pooling model.
- Evidence binaries are stored separately from relational metadata. Object keys are opaque; authorization is checked before every read/write.
- Raw payment/customer payloads are not logged. Minimize and redact personal/payment data at ingestion.
- External integrations are untrusted inputs. Validate schemas, lengths, content types, identifiers, timestamps, currency and numeric ranges.
- Webhooks require signature verification, replay protection, idempotency and bounded retries if introduced.
- No secret, token, credential or private key is committed to source control.

## Risk-engine contract

Every result includes result ID/time, rule/model version, configuration digest, input provenance, feature availability, score semantics, reason codes, anomaly output distinct from calibrated fraud probability, limitations, missing-data/abstention state and human-review recommendation. It never makes an automatic payment decision.

Model promotion requires independent permissioned labelled data; train/test separation; leakage checks; class-imbalance handling; calibration; precision/recall and false-positive/negative analysis; subgroup and drift monitoring; reproducible artifacts; and rollback. Until then, outputs remain demonstrative.

## API and compatibility

Version external APIs (for example /api/v1); use explicit schemas; reject malformed security-sensitive fields; make create/import idempotent; use UTC and decimal-safe money with ISO currency codes; paginate and bound exports; return safe machine-readable errors; and maintain audit-export compatibility tests.

## Proposed technology baseline

Python 3.12+ with FastAPI/Pydantic; React + TypeScript; PostgreSQL; versioned object storage; pytest/Hypothesis/Playwright; Ruff/mypy; pinned dependencies; CodeQL/Semgrep/Trivy/secret scanning/SBOM; OWASP ZAP; OpenTelemetry-compatible observability. Verify current compatibility before pinning versions.

## Initial non-goals

Autonomous payment blocking/approval; fraud accuracy claims without external validation; universal bank/exchange connectors without contracts and test environments; legal/compliance certification claims without independent assessment; blockchain immutability claims based only on hashes.