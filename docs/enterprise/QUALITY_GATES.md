# FraudShield Enterprise X — Quality and Release Gates

A release is blocked unless each applicable gate has a recorded result and evidence. Not run is not passed.

## A — Functional correctness

- Unit tests for money, currency, validation, rules, scoring, state transitions and serialization.
- Property tests for numeric boundaries, malformed input, Unicode, timestamps and parsers.
- API contract and database migration tests.
- End-to-end tests for case, intake, review, evidence, report export and permission denial.
- Regression tests for every fixed defect.

## B — Security

- Threat model updated against implementation.
- SAST, dependency scan, secret scan and SBOM.
- DAST against disposable deployment.
- Authorization matrix including cross-tenant attempts.
- Upload, parser, SSRF, rate-limit and abuse tests.
- No unresolved Critical/High findings. Medium findings require documented treatment and owner.

## C — Evidence and audit

- Digest reproducibility and tamper detection.
- Version and custody-event sequencing.
- Authorization on every evidence operation.
- Audit events for security-sensitive state changes.
- Backup/restore test preserving metadata and object references.
- Explicit distinction between digest verification and authenticity.

## D — Reliability and performance

- Health/readiness checks and graceful dependency failure.
- Bounded retries, timeouts and idempotent writes.
- Load test against documented workload.
- No unbounded memory/file parsing.
- Recovery objectives and restore evidence documented.
- No silent data loss on worker or integration failure.

## E — UX and accessibility

- Keyboard navigation, visible focus, semantic labels and accessible status messages.
- Clear distinction between synthetic, manual and externally verified data.
- Empty, loading, error and permission-denied states.
- Human-review workflow tested with realistic task scripts.

## F — Packaging

- Reproducible locked dependencies and build.
- Versioned API and migrations.
- Deployment and rollback instructions.
- Configuration/secrets checklist, user/admin docs and limitations.
- Forge app independently installed/tested in clean developer site.
- Demo reflects submitted commit and working functionality.

## 100-point scorecard

| Area | Weight |
|---|---:|
| Functional correctness | 20 |
| Security and privacy | 20 |
| Architecture and maintainability | 15 |
| Evidence and audit integrity | 15 |
| Tests and reliability | 15 |
| UX and integration | 10 |
| Documentation and packaging | 5 |
| **Total** | **100** |

A score cannot override a release blocker. Any unresolved critical/high vulnerability, cross-tenant exposure, failed core acceptance test or unverified backup blocks release regardless of numeric score.