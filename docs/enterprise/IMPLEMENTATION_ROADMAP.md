# FraudShield Enterprise X — Implementation Roadmap

Baseline: existing FraudShield AI prototype on main. Working branch: enterprise/fraudshield-enterprise-x-foundation. Preserve the prototype and keep ProofGap X repositories untouched.

## Phase 0 — Baseline and discovery

Freeze baseline commit; inventory modules, tests, secrets, dependencies, workflows and deployment settings; run tests/compilation in a clean environment; map implemented behavior against README; produce reproducible defect register. Exit: baseline report and no unclassified production-facing behavior.

## Phase 1 — Contracts and foundation

Define domain entities, API schemas, tenant/role/permission model, migrations, object-storage interface, audit event schema and evidence custody lifecycle. Establish locked dependencies, lint/type checks and CI security gates. Exit: reviewed architecture and passing contract/migration tests.

## Phase 2 — Secure commercial core

Authentication and tenant membership; cases, assignments, timeline and notes; transaction intake with idempotency/provenance; evidence upload/download with versioning/access control; append-only audit interface; exports and reports. Exit: end-to-end acceptance suite including cross-tenant denial.

## Phase 3 — Risk intelligence governance

Versioned rules and reason codes; separate anomaly output from fraud probability; missing-data handling and abstention; dataset governance and independent evaluation harness. Exit: reproducible evaluation report and no unsupported accuracy claims.

## Phase 4 — Atlassian Codegeist application

Forge app with minimum scopes; Jira case synchronization with idempotency; Confluence report generation with data minimization; permission review; clean-site install/uninstall and failure-path tests. Exit: working install and demonstrable end-to-end workflow.

## Phase 5 — Enterprise assurance

Security testing/remediation; load, backup/restore and recovery tests; accessibility/usability review; deployment profiles, admin guide, incident response and upgrade guide; independent review of critical controls. Exit: all release gates pass with artifacts.

## Phase 6 — Commercial readiness

Pilot package using synthetic or customer-authorized data; buyer-specific demo and pilot success criteria; license/support/data processing/deployment options reviewed; pricing validated through buyer discovery. Exit: repeatable installation, evidence pack and pilot proposal.