# FraudShield Enterprise X — Initial Threat Model

Status: initial design review; update against implemented data flows and deployment configuration.

## Assets

1. Tenant transaction and case records.
2. Evidence files and acquisition metadata.
3. Identity credentials, API tokens and integration secrets.
4. Audit events and report exports.
5. Risk rules, model artifacts and configuration.
6. Availability and integrity of investigation workflows.

## Trust boundaries

Browser/API; tenant/tenant; API/PostgreSQL; API/object storage; core/external adapters; Forge/Atlassian and core API; CI runner/source/package registries/secrets; administrator/production control plane.

## Threats and controls

| Threat | Required control | Verification evidence |
|---|---|---|
| Cross-tenant exposure (IDOR/BOLA) | Server-side tenant authorization on every object; deny by default; database defense in depth | Two-tenant negative tests for read/update/delete/export/evidence URLs |
| Credential theft | Managed secrets, rotation, least privilege, no secret logging, secret scanning | Secret scan, log inspection and rotation runbook |
| Malicious/oversized upload | Size/type limits, content sniffing, safe names, storage outside web root | Fuzzed upload and storage authorization tests |
| Evidence substitution | Versioned object storage, acquisition digest, custody events, restricted deletion | Mutation, replacement, replay and restore tests |
| Forged/replayed webhook | Signature verification, timestamp tolerance, replay store, idempotency | Invalid signature and replay suite |
| Injection | Parameterized queries, safe subprocess boundaries, output encoding | SAST, DAST and adversarial tests |
| SSRF | Destination allowlists, DNS/IP validation, redirect policy, timeouts, egress controls | Private/link-local target regression tests |
| Resource exhaustion | Request/upload limits, pagination, rate limits, bounded parsing and worker quotas | Load and abuse tests |
| Audit repudiation | Authenticated actor attribution, append-only interface, protected key/storage separation | Privilege-abuse and tamper-evidence tests |
| Supply-chain compromise | Pinned dependencies, lockfiles, SBOM, provenance, dependency review | CI dependency and image scans |
| Misleading/manipulated model | Versioned models, input provenance, human review, abstention and limitations | Governance tests and evaluation report |
| Forge permission overreach | Minimum scopes, explicit consent, tenant-aware app data | Permission review and clean-site installation test |

## Security invariants

- A user cannot access another tenant's data by changing an identifier, URL or export parameter.
- Client-supplied tenant IDs are never authorization.
- Secrets, access tokens and sensitive upstream errors are never returned to browser or logs.
- Digest match is described as content-integrity verification, not authenticity or proof of custody.
- Risk outputs never trigger payment decisions in the initial product.
- Integration failure cannot corrupt or erase the core case record.
- Security-sensitive operations are attributable and audited.

## Residual risks

Privileged infrastructure administrators may alter data without independent WORM/retention controls. SHA-256 alone cannot prove who acquired evidence, when, or source genuineness. Synthetic model data cannot establish real-world performance. Integrations inherit upstream availability and data-quality constraints. Jurisdiction-specific retention, residency and financial-sector duties require customer review.